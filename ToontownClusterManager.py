import subprocess
import time
from datetime import datetime
from threading import Thread
import sys
import signal
import os

try:
    from Queue import Queue, Empty
except ImportError:
    from queue import Queue, Empty # for Python 3.x

NUM_SERVERS = 4

SERVER_PLATFORM = ""

DEFAULT_UBERDOG_CHANNEL = 1000000

START_ASTRON_CLUSTER_FILE = "start-astron-cluster"
START_UBERDOG_SERVER_FILE = "start-uberdog-server"
START_AI_SERVER_FILE = "start-ai-server"

if sys.platform == "linux" or sys.platform == "linux2" or sys.platform == "darwin":
    START_ASTRON_CLUSTER_FILE = "./" + START_ASTRON_CLUSTER_FILE + ".sh"
    START_UBERDOG_SERVER_FILE = "./" + START_UBERDOG_SERVER_FILE + ".sh"
    START_AI_SERVER_FILE = "./" + START_AI_SERVER_FILE + ".sh"
    SERVER_PLATFORM = "linux"

elif sys.platform == "win32":
    START_ASTRON_CLUSTER_FILE += ".bat"
    START_UBERDOG_SERVER_FILE += ".bat"
    START_AI_SERVER_FILE += ".bat"
    SERVER_PLATFORM = "win32"

def launch_without_console(command, args):
    """Launches 'command' windowless"""
    startupinfo = None
    if SERVER_PLATFORM == "win32":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

    return subprocess.Popen([command] + args, startupinfo=startupinfo,
                            stderr=subprocess.PIPE, stdout=subprocess.PIPE)

def start_astron():
    process = launch_without_console(START_ASTRON_CLUSTER_FILE, [])
    return process

def start_uberdog(channel):
    process = launch_without_console(START_UBERDOG_SERVER_FILE, [str(channel)])
    return process


def start_ai_server(number):
    process = launch_without_console(START_AI_SERVER_FILE, [str(number)])
    return process


def enqueue_output(out, queue, prefix, process):
    for line in iter(out.readline, b''):
        if line != '':
            queue.append((prefix + line.decode('utf-8')).strip())
    out.close()

def print_output(queue):
    while queue:
        line = queue.pop(0)
        print(datetime.now().strftime("%Y-%m-%d %H:%M:%S") + ' - ' + line)

def shutdown_handler():
    print("Killing all processes")
    for process in processes + [astron, uberdog]:
        os.killpg(os.getpgid(process.pid), signal.SIGTERM)

    sys.exit()

if __name__ == "__main__":
    os.chdir("astron/" + SERVER_PLATFORM + "/")
    processes = []
    q = []
    threads = []

    print("Starting astron")
    astron = start_astron()
    print("Starting uberdog")
    uberdog = start_uberdog(DEFAULT_UBERDOG_CHANNEL)

    def signal_term_handler(s, frame):
        shutdown_handler()

    signal.signal(signal.SIGINT, signal_term_handler)

    for i in range(int(input('Number of districts?: '))):
        processes.append(start_ai_server(i + 1))
        print("Started Server " + str(i+1))
        time.sleep(1)

    threads.append(Thread(target=enqueue_output, args=(astron.stderr, q, "[Astron]:: ", astron)))
    threads.append(Thread(target=enqueue_output, args=(astron.stdout, q, "[Astron]:: ", astron)))
    threads.append(Thread(target=enqueue_output, args=(uberdog.stderr, q, "[Uberdog]:: ", uberdog)))
    threads.append(Thread(target=enqueue_output, args=(uberdog.stdout, q, "[Uberdog]:: ", uberdog)))

    i = 1
    for p in processes:
        threads.append(Thread(target=enqueue_output, args=(p.stdout, q, "[District %s]:: " % (i), p)))
        threads.append(Thread(target=enqueue_output, args=(p.stderr, q, "[District %s]:: " %(i), p)))
        i += 1

    for t in threads:
        t.daemon = True
        t.start()

    while True:
        print_output(q)

        #break when all processes are done.
        if all(p.poll() is not None for p in processes):
            break

    print('All processes done')
