#!/usr/bin/env python2
import __builtin__


__builtin__.process = 'client'


# Temporary hack patch:
__builtin__.__dict__.update(__import__('panda3d.core', fromlist=['*']).__dict__)
from direct.extensions_native import HTTPChannel_extensions
from direct.extensions_native import Mat3_extensions
from direct.extensions_native import VBase3_extensions
from direct.extensions_native import VBase4_extensions
from direct.extensions_native import NodePath_extensions


from panda3d.core import loadPrcFile


if __debug__:
    loadPrcFile('config/general.prc')
    loadPrcFile('config/release/dev.prc')


from direct.directnotify.DirectNotifyGlobal import directNotify


notify = directNotify.newCategory('ClientStart')
notify.setInfo(True)


from otp.settings.Settings import Settings


preferencesFilename = ConfigVariableString(
    'preferences-filename', 'preferences.json').getValue()
notify.info('Reading %s...' % preferencesFilename)
__builtin__.settings = Settings(preferencesFilename)
if 'fullscreen' not in settings:
    settings['fullscreen'] = False
if 'music' not in settings:
    settings['music'] = True
if 'sfx' not in settings:
    settings['sfx'] = True
if 'musicVol' not in settings:
    settings['musicVol'] = 1.0
if 'sfxVol' not in settings:
    settings['sfxVol'] = 1.0
if 'loadDisplay' not in settings:
    settings['loadDisplay'] = 'pandagl'
if 'toonChatSounds' not in settings:
    settings['toonChatSounds'] = True
loadPrcFileData('Settings: res', 'win-size %d %d' % tuple(settings.get('res', (800, 600))))
loadPrcFileData('Settings: fullscreen', 'fullscreen %s' % settings['fullscreen'])
loadPrcFileData('Settings: music', 'audio-music-active %s' % settings['music'])
loadPrcFileData('Settings: sfx', 'audio-sfx-active %s' % settings['sfx'])
loadPrcFileData('Settings: musicVol', 'audio-master-music-volume %s' % settings['musicVol'])
loadPrcFileData('Settings: sfxVol', 'audio-master-sfx-volume %s' % settings['sfxVol'])
loadPrcFileData('Settings: loadDisplay', 'load-display %s' % settings['loadDisplay'])
loadPrcFileData('Settings: toonChatSounds', 'toon-chat-sounds %s' % settings['toonChatSounds'])


import os

from toontown.toonbase.ContentPacksManager import ContentPackError
from toontown.toonbase.ContentPacksManager import ContentPacksManager


contentPacksFilepath = ConfigVariableString(
    'content-packs-filepath', 'contentpacks/').getValue()
contentPacksSortFilename = ConfigVariableString(
    'content-packs-sort-filename', 'sort.yaml').getValue()
if not os.path.exists(contentPacksFilepath):
    os.makedirs(contentPacksFilepath)
__builtin__.ContentPackError = ContentPackError
__builtin__.contentPacksMgr = ContentPacksManager(
    filepath=contentPacksFilepath, sortFilename=contentPacksSortFilename)
contentPacksMgr.applyAll()


import time
import sys
import random
import __builtin__
try:
    launcher
except:
    from toontown.launcher.TTILauncher import TTILauncher
    launcher = TTILauncher()
    __builtin__.launcher = launcher


notify.info('Starting the game...')
if launcher.isDummy():
    http = HTTPClient()
else:
    http = launcher.http
tempLoader = Loader()
backgroundNode = tempLoader.loadSync(Filename('phase_3/models/gui/loading-background'))
from direct.gui import DirectGuiGlobals
from direct.gui.DirectGui import *
notify.info('Setting the default font...')
import ToontownGlobals
DirectGuiGlobals.setDefaultFontFunc(ToontownGlobals.getInterfaceFont)
launcher.setPandaErrorCode(7)
import ToonBase
ToonBase.ToonBase()
from panda3d.core import *
if base.win is None:
    notify.error('Unable to open window; aborting.')
launcher.setPandaErrorCode(0)
launcher.setPandaWindowOpen()
ConfigVariableDouble('decompressor-step-time').setValue(0.01)
ConfigVariableDouble('extractor-step-time').setValue(0.01)
backgroundNodePath = aspect2d.attachNewNode(backgroundNode, 0)
backgroundNodePath.setPos(0.0, 0.0, 0.0)
backgroundNodePath.setScale(render2d, VBase3(1))
backgroundNodePath.find('**/fg').hide()
logo = OnscreenImage(
    image='phase_3/maps/toontown-logo.png',
    scale=(1 / (4.0/3.0), 1, 1 / (4.0/3.0)),
    pos=backgroundNodePath.find('**/fg').getPos())
logo.setTransparency(TransparencyAttrib.MAlpha)
logo.setBin('fixed', 20)
logo.reparentTo(backgroundNodePath)
backgroundNodePath.find('**/bg').setBin('fixed', 10)
base.graphicsEngine.renderFrame()
DirectGuiGlobals.setDefaultRolloverSound(base.loader.loadSfx('phase_3/audio/sfx/GUI_rollover.ogg'))
DirectGuiGlobals.setDefaultClickSound(base.loader.loadSfx('phase_3/audio/sfx/GUI_create_toon_fwd.ogg'))
DirectGuiGlobals.setDefaultDialogGeom(loader.loadModel('phase_3/models/gui/dialog_box_gui'))
import TTLocalizer
from otp.otpbase import OTPGlobals
OTPGlobals.setDefaultProductPrefix(TTLocalizer.ProductPrefix)
if base.musicManagerIsValid:
    themeList = ('phase_3/audio/bgm/tti_theme.ogg', 'phase_3/audio/bgm/tti_theme_2.ogg')
    music = base.loader.loadMusic(random.choice(themeList))
    if music:
        music.setLoop(1)
        music.setVolume(0.9)
        music.play()
    notify.info('Loading the default GUI sounds...')
    DirectGuiGlobals.setDefaultRolloverSound(base.loader.loadSfx('phase_3/audio/sfx/GUI_rollover.ogg'))
    DirectGuiGlobals.setDefaultClickSound(base.loader.loadSfx('phase_3/audio/sfx/GUI_create_toon_fwd.ogg'))
else:
    music = None
import ToontownLoader
from direct.gui.DirectGui import *
serverVersion = base.config.GetString('server-version', 'no_version_set')
version = OnscreenText(serverVersion, pos=(-1.3, -0.975), scale=0.06, fg=Vec4(0, 0, 0, 1), align=TextNode.ALeft)
version.setPos(0.03,0.03)
version.reparentTo(base.a2dBottomLeft)
from toontown.suit import Suit
Suit.loadModels()
loader.beginBulkLoad('init', TTLocalizer.LoaderLabel, 138, 0, TTLocalizer.TIP_NONE, 0)
from ToonBaseGlobal import *
from direct.showbase.MessengerGlobal import *
from toontown.distributed import ToontownClientRepository
cr = ToontownClientRepository.ToontownClientRepository(serverVersion, launcher)
cr.music = music
del music
base.initNametagGlobals()
base.cr = cr
loader.endBulkLoad('init')
from otp.friends import FriendManager
from otp.distributed.OtpDoGlobals import *
cr.generateGlobalObject(OTP_DO_ID_FRIEND_MANAGER, 'FriendManager')
if not launcher.isDummy():
    base.startShow(cr, launcher.getGameServer())
else:
    base.startShow(cr)
backgroundNodePath.reparentTo(hidden)
backgroundNodePath.removeNode()
del backgroundNodePath
del backgroundNode
del tempLoader
version.cleanup()
del version
base.loader = base.loader
__builtin__.loader = base.loader

'''
"Injector"
added by freshollie
Works exactly like the conventional injector

Also includes modloader. Any files places in mods/ will
be attempted to execute
'''

import Tkinter
import traceback
import os
import __main__


class Injector(object):
    def __init__(self):
        self.firstTick = True
        self.loading = None
        self.root = Tkinter.Tk()
        title = 'Injector'
        self.root.title(title)

        f = Tkinter.Frame(self.root)
        f.pack()

        xscrollbar = Tkinter.Scrollbar(f, orient=Tkinter.HORIZONTAL)
        xscrollbar.grid(row=1, column=0, sticky=Tkinter.N + Tkinter.S + Tkinter.E + Tkinter.W)

        yscrollbar = Tkinter.Scrollbar(f)
        yscrollbar.grid(row=0, column=1, sticky=Tkinter.N + Tkinter.S + Tkinter.E + Tkinter.W)

        self.text = Tkinter.Text(f, wrap=Tkinter.NONE,
                                 xscrollcommand=xscrollbar.set,
                                 yscrollcommand=yscrollbar.set)
        self.text.bind("<Control-Key-a>", self.select_all)
        self.text.bind("<Control-Key-A>", self.select_all)
        self.text.grid(row=0, column=0)

        xscrollbar.config(command=self.text.xview)
        yscrollbar.config(command=self.text.yview)

        self.button = Tkinter.Button(self.root, text='Inject', command=self.pressed)
        self.button.pack()

    def select_all(self, event):
        self.text.tag_add(Tkinter.SEL, "1.0", Tkinter.END)
        self.text.mark_set(Tkinter.INSERT, "1.0")
        self.text.see(Tkinter.INSERT)
        return 'break'

    def pressed(self):
        exec injection in __main__.__dict__

    def loadScripts(self):
        if not os.path.exists('mods'):
            os.makedirs('mods')
        for scriptName in os.listdir('mods'):
            split = scriptName.split('.')
            if len(split) > 1:
                try:
                    execfile('mods/' + scriptName, globals())
                except Exception, err:
                    print(traceback.format_exc())
        self.firstTick = False

    def tick(self, task):
        if self.firstTick:
            self.loadScripts()
            self.firstTick = False
        else:
            self.root.update()
        return task.cont


injector = Injector()

injection = '''
try:
    contents = injector.text.get(1.0, Tkinter.END)
    exec(contents,globals(),locals())
except Exception, err:
    print(traceback.format_exc())
'''
taskMgr.add(injector.tick, 'test')

autoRun = ConfigVariableBool('toontown-auto-run', 1)
if autoRun:
    try:
        base.run()
    except SystemExit:
        raise
    except:
        from toontown.util import PythonUtil
        print PythonUtil.describeException()
        raise
