import types
import time
from direct.distributed.ClockDelta import *
from direct.gui.DirectGui import *
from panda3d.core import *
from direct.interval.IntervalGlobal import ivalMgr
from direct.directnotify import DirectNotifyGlobal
from direct.distributed import DistributedSmoothNode
from direct.distributed.PyDatagram import PyDatagram
from direct.distributed.PyDatagramIterator import PyDatagramIterator
from direct.task import Task
from direct.fsm import ClassicFSM
from direct.fsm import State
from toontown.util.PythonUtil import Functor, ScratchPad
from direct.showbase.InputStateGlobal import inputState
from otp.avatar import Avatar
from otp.avatar import DistributedAvatar
from otp.friends import FriendManager
from otp.login import HTTPUtil
from otp.distributed import OTPClientRepository
from otp.distributed import PotentialAvatar
from otp.distributed import PotentialShard
from otp.distributed import DistributedDistrict
from otp.distributed.OtpDoGlobals import *
from otp.distributed import OtpDoGlobals
from otp.otpbase import OTPGlobals
from otp.otpbase import OTPLocalizer
from otp.otpbase import OTPLauncherGlobals
from otp.avatar.Avatar import teleportNotify
from toontown.toonbase.ToonBaseGlobal import *
from toontown.toonbase.ToontownGlobals import *
from toontown.launcher.DownloadForceAcknowledge import *
from toontown.distributed import DelayDelete
from toontown.friends import FriendHandle
from toontown.friends import FriendsListPanel
from toontown.friends import ToontownFriendSecret
from toontown.uberdog import TTSpeedchatRelay
from toontown.login import DateObject
from toontown.login import AvatarChooser
from toontown.makeatoon import MakeAToon
from toontown.pets import DistributedPet, PetDetail, PetHandle
from toontown.toonbase import TTLocalizer
from toontown.toontowngui import TTDialog
from toontown.toon import LocalToon
from toontown.toon import ToonDNA
from toontown.distributed import ToontownDistrictStats
from toontown.makeatoon import TTPickANamePattern
from toontown.parties import ToontownTimeManager
from toontown.toon import Toon, DistributedToon
from ToontownMsgTypes import *
import HoodMgr
import PlayGame
from toontown.toontowngui import ToontownLoadingBlocker
from toontown.hood import StreetSign
import random


class ToontownClientRepository(OTPClientRepository.OTPClientRepository):
    SupportTutorial = 1
    GameGlobalsId = OTP_DO_ID_TOONTOWN
    SetZoneDoneEvent = 'TCRSetZoneDone'
    EmuSetZoneDoneEvent = 'TCREmuSetZoneDone'
    SetInterest = 'Set'
    ClearInterest = 'Clear'
    ClearInterestDoneEvent = 'TCRClearInterestDone'
    KeepSubShardObjects = False

    def __init__(self, serverVersion, launcher = None):
        OTPClientRepository.OTPClientRepository.__init__(self, serverVersion, launcher, playGame=PlayGame.PlayGame)
        self._playerAvDclass = self.dclassesByName['DistributedToon']
        setInterfaceFont(TTLocalizer.InterfaceFont)
        setSignFont(TTLocalizer.SignFont)
        setFancyFont(TTLocalizer.FancyFont)
        for i in xrange(len(TTLocalizer.NametagFonts)):
            setNametagFont(i, TTLocalizer.NametagFonts[i])

        self.toons = {}
        if self.http.getVerifySsl() != HTTPClient.VSNoVerify:
            self.http.setVerifySsl(HTTPClient.VSNoDateCheck)
        self.__forbidCheesyEffects = 0
        self.friendManager = None
        self.speedchatRelay = None
        self.trophyManager = None
        self.bankManager = None
        self.catalogManager = None
        self.tutorialManager = None
        self.welcomeValleyManager = None
        self.newsManager = None
        self.streetSign = None
        self.distributedDistrict = None
        self.partyManager = None
        self.inGameNewsMgr = None
        self.whitelistMgr = None

        self.toontownTimeManager = ToontownTimeManager.ToontownTimeManager()

        self.csm = self.generateGlobalObject(OtpDoGlobals.OTP_DO_ID_CLIENT_SERVICES_MANAGER, 'ClientServicesManager')
        self.avatarFriendsManager = self.generateGlobalObject(OtpDoGlobals.OTP_DO_ID_AVATAR_FRIENDS_MANAGER, 'AvatarFriendsManager')
        self.playerFriendsManager = self.generateGlobalObject(OtpDoGlobals.OTP_DO_ID_PLAYER_FRIENDS_MANAGER, 'TTPlayerFriendsManager')
        self.ttiFriendsManager = self.generateGlobalObject(OtpDoGlobals.OTP_DO_ID_TTI_FRIENDS_MANAGER, 'TTIFriendsManager')
        self.speedchatRelay = self.generateGlobalObject(OtpDoGlobals.OTP_DO_ID_TOONTOWN_SPEEDCHAT_RELAY, 'TTSpeedchatRelay')
        self.deliveryManager = self.generateGlobalObject(OtpDoGlobals.OTP_DO_ID_TOONTOWN_DELIVERY_MANAGER, 'DistributedDeliveryManager')
        if config.GetBool('want-code-redemption', 1):
            self.codeRedemptionManager = self.generateGlobalObject(OtpDoGlobals.OTP_DO_ID_TOONTOWN_CODE_REDEMPTION_MANAGER, 'TTCodeRedemptionMgr')

        self.streetSign = None
        self.furnitureManager = None
        self.objectManager = None
        self.openAvatarPanels = set()
        self.friendsMap = {}
        self.friendsOnline = {}
        self.friendsMapPending = 0
        self.friendsListError = 0
        self.friendPendingChatSettings = {}
        self.elderFriendsMap = {}
        self.__queryAvatarMap = {}
        self.dateObject = DateObject.DateObject()
        self.hoodMgr = HoodMgr.HoodMgr(self)
        self.setZonesEmulated = 0
        self.old_setzone_interest_handle = None
        self.setZoneQueue = Queue()
        self.accept(ToontownClientRepository.SetZoneDoneEvent, self._handleEmuSetZoneDone)
        self._deletedSubShardDoIds = set()
        self.toonNameDict = {}
        self.gameFSM.addState(State.State('skipTutorialRequest', self.enterSkipTutorialRequest, self.exitSkipTutorialRequest, ['playGame', 'gameOff', 'tutorialQuestion']))
        state = self.gameFSM.getStateNamed('waitOnEnterResponses')
        state.addTransition('skipTutorialRequest')
        state = self.gameFSM.getStateNamed('playGame')
        state.addTransition('skipTutorialRequest')
        self.wantCogdominiums = base.config.GetBool('want-cogdominiums', 1)
        self.wantEmblems = base.config.GetBool('want-emblems', 0)
        if base.config.GetBool('tt-node-check', 0):
            for species in ToonDNA.toonSpeciesTypes:
                for head in ToonDNA.getHeadList(species):
                    for torso in ToonDNA.toonTorsoTypes:
                        for legs in ToonDNA.toonLegTypes:
                            for gender in ('m', 'f'):
                                print 'species: %s, head: %s, torso: %s, legs: %s, gender: %s' % (species,
                                 head,
                                 torso,
                                 legs,
                                 gender)
                                dna = ToonDNA.ToonDNA()
                                dna.newToon((head,
                                 torso,
                                 legs,
                                 gender))
                                toon = Toon.Toon()
                                try:
                                    toon.setDNA(dna)
                                except Exception, e:
                                    print e

        return

    def congratulations(self, avatarChoice):
        self.acceptedScreen = loader.loadModel('phase_3/models/gui/toon_council')
        self.acceptedScreen.setScale(0.667)
        self.acceptedScreen.reparentTo(aspect2d)
        base.setBackgroundColor(Vec4(0.7647, 0.3529, 0.2352, 1))
        buttons = loader.loadModel('phase_3/models/gui/dialog_box_buttons_gui')
        self.acceptedBanner = DirectLabel(parent=self.acceptedScreen, relief=None, text=OTPLocalizer.CRNameCongratulations, text_scale=0.18, text_fg=Vec4(0.6, 0.1, 0.1, 1), text_pos=(0, 0.05), text_font=getMinnieFont())
        newName = avatarChoice.approvedName
        self.acceptedText = DirectLabel(parent=self.acceptedScreen, relief=None, text=OTPLocalizer.CRNameAccepted % newName, text_scale=0.125, text_fg=Vec4(0, 0, 0, 1), text_pos=(0, -0.15))
        self.okButton = DirectButton(parent=self.acceptedScreen, image=(buttons.find('**/ChtBx_OKBtn_UP'), buttons.find('**/ChtBx_OKBtn_DN'), buttons.find('**/ChtBx_OKBtn_Rllvr')), relief=None, text='Ok', scale=1.5, text_scale=0.05, text_pos=(0.0, -0.1), pos=(0, 0, -1), command=self.__handleCongrats, extraArgs=[avatarChoice])
        buttons.removeNode()
        base.transitions.noFade()
        return

    def __handleCongrats(self, avatarChoice):
        self.acceptedBanner.destroy()
        self.acceptedText.destroy()
        self.okButton.destroy()
        self.acceptedScreen.removeNode()
        del self.acceptedScreen
        del self.okButton
        del self.acceptedText
        del self.acceptedBanner
        base.setBackgroundColor(ToontownGlobals.DefaultBackgroundColor)
        self.csm.sendAcknowledgeAvatarName(
            avatarChoice.id,
            lambda: self.loginFSM.request('waitForSetAvatarResponse', [avatarChoice]))

    def betterlucknexttime(self, avList, index):
        self.rejectDoneEvent = 'rejectDone'
        self.rejectDialog = TTDialog.TTGlobalDialog(doneEvent=self.rejectDoneEvent, message=TTLocalizer.NameShopNameRejected, style=TTDialog.Acknowledge)
        self.rejectDialog.show()
        self.acceptOnce(self.rejectDoneEvent, self.__handleReject, [avList, index])
        base.transitions.noFade()

    def __handleReject(self, avList, index):
        self.rejectDialog.cleanup()
        avid = 0
        for k in avList:
            if k.position == index:
                avid = k.id

        if avid == 0:
            self.notify.error('Avatar rejected not found in avList.  Index is: ' + str(index))
        self.csm.sendAcknowledgeAvatarName(
            avid,
            lambda: self.loginFSM.request('waitForAvatarList'))

    def enterChooseAvatar(self, avList):
        ModelPool.garbageCollect()
        TexturePool.garbageCollect()
        self.sendSetAvatarIdMsg(0)
        self.clearFriendState()
        if self.music == None and base.musicManagerIsValid:
            themeList = ('phase_3/audio/bgm/tti_theme.ogg', 'phase_3/audio/bgm/tti_theme_2.ogg')
            self.music = base.musicManager.getSound(random.choice(themeList))
            if self.music:
                self.music.setLoop(1)
                self.music.setVolume(0.9)
                self.music.play()
        base.playMusic(self.music, looping=1, volume=0.9, interrupt=None)
        self.handler = self.handleMessageType
        self.avChoiceDoneEvent = 'avatarChooserDone'
        self.avChoice = AvatarChooser.AvatarChooser(avList, self.loginFSM, self.avChoiceDoneEvent)
        self.avChoice.load(self.isPaid())
        self.avChoice.enter()
        self.accept(self.avChoiceDoneEvent, self.__handleAvatarChooserDone, [avList])
        if config.GetBool('want-gib-loader', 1):
            self.loadingBlocker = ToontownLoadingBlocker.ToontownLoadingBlocker(avList)
        return

    def __handleAvatarChooserDone(self, avList, doneStatus):
        done = doneStatus['mode']
        if done == 'exit':
            self.loginFSM.request('shutdown')
        index = self.avChoice.getChoice()
        for av in avList:
            if av.position == index:
                avatarChoice = av
                dna = ToonDNA.ToonDNA()
                dna.makeFromNetString(av.dna)
                print '__handleAvatarChooserDone: %r, %r, %r, %r' % (av.id, av.name, dna.asTuple(), av.position)

        if done == 'chose':
            self.avChoice.exit()
            if avatarChoice.approvedName != '':
                self.congratulations(avatarChoice)
                avatarChoice.approvedName = ''
            elif avatarChoice.rejectedName != '':
                avatarChoice.rejectedName = ''
                self.betterlucknexttime(avList, index)
            else:
                base.localAvatarStyle = dna
                base.localAvatarName = avatarChoice.name
                self.loginFSM.request('waitForSetAvatarResponse', [avatarChoice])
        elif done == 'nameIt':
            self.accept('downloadAck-response', self.__handleDownloadAck, [avList, index])
            self.downloadAck = DownloadForceAcknowledge('downloadAck-response')
            self.downloadAck.enter(4)
        elif done == 'create':
            self.loginFSM.request('createAvatar', [avList, index])
        elif done == 'delete':
            self.loginFSM.request('waitForDeleteAvatarResponse', [avatarChoice])

    def __handleDownloadAck(self, avList, index, doneStatus):
        if doneStatus['mode'] == 'complete':
            self.goToPickAName(avList, index)
        else:
            self.loginFSM.request('chooseAvatar', [avList])
        self.downloadAck.exit()
        self.downloadAck = None
        self.ignore('downloadAck-response')
        return

    def exitChooseAvatar(self):
        self.handler = None
        self.avChoice.exit()
        self.avChoice.unload()
        self.avChoice = None
        self.ignore(self.avChoiceDoneEvent)
        return

    def goToPickAName(self, avList, index):
        self.avChoice.exit()
        self.loginFSM.request('createAvatar', [avList, index])

    def enterCreateAvatar(self, avList, index, newDNA = None):
        if self.music:
            self.music.stop()
            self.music = None
        if newDNA != None:
            self.newPotAv = PotentialAvatar.PotentialAvatar('deleteMe', ['',
             '',
             '',
             ''], newDNA.makeNetString(), index, 1)
            avList.append(self.newPotAv)
        base.transitions.noFade()
        self.avCreate = MakeAToon.MakeAToon(self.loginFSM, avList, 'makeAToonComplete', index, self.isPaid())
        self.avCreate.load()
        self.avCreate.enter()
        self.accept('makeAToonComplete', self.__handleMakeAToon, [avList, index])
        self.accept('nameShopPost', self.relayMessage)
        return

    def relayMessage(self, dg):
        self.send(dg)

    def __handleMakeAToon(self, avList, avPosition):
        done = self.avCreate.getDoneStatus()
        if done == 'cancel':
            if hasattr(self, 'newPotAv'):
                if self.newPotAv in avList:
                    avList.remove(self.newPotAv)
            self.avCreate.exit()
            self.loginFSM.request('chooseAvatar', [avList])
        elif done == 'created':
            self.avCreate.exit()
            if not base.launcher or base.launcher.getPhaseComplete(3.5):
                for i in avList:
                    if i.position == avPosition:
                        newPotAv = i

                self.loginFSM.request('waitForSetAvatarResponse', [newPotAv])
            else:
                self.loginFSM.request('chooseAvatar', [avList])
        else:
            self.notify.error('Invalid doneStatus from MakeAToon: ' + str(done))

    def exitCreateAvatar(self):
        self.ignore('makeAToonComplete')
        self.ignore('nameShopPost')
        self.avCreate.unload()
        self.avCreate = None
        self.handler = None
        if hasattr(self, 'newPotAv'):
            del self.newPotAv
        return

    def handleAvatarResponseMsg(self, avatarId, di):
        self.cleanupWaitingForDatabase()
        dclass = self.dclassesByName['DistributedToon']
        NametagGlobals.setWant2dNametags(False)
        loader.beginBulkLoad('localAvatarPlayGame', OTPLocalizer.CREnteringToontown, 400, 1, TTLocalizer.TIP_GENERAL, 0)
        localAvatar = LocalToon.LocalToon(self)
        localAvatar.dclass = dclass
        base.localAvatar = localAvatar
        __builtins__['localAvatar'] = base.localAvatar
        NametagGlobals.setMe(base.localAvatar)
        localAvatar.doId = avatarId
        self.localAvatarDoId = avatarId
        parentId = None
        zoneId = None
        localAvatar.setLocation(parentId, zoneId)
        localAvatar.generateInit()
        localAvatar.generate()
        dclass.receiveUpdateBroadcastRequiredOwner(localAvatar, di)
        localAvatar.announceGenerate()
        localAvatar.postGenerateMessage()
        self.doId2do[avatarId] = localAvatar
        localAvatar.initInterface()
        self.sendGetFriendsListRequest()
        self.loginFSM.request('playingGame')

    def getAvatarDetails(self, avatar, func, *args):
        pad = ScratchPad()
        pad.func = func
        pad.args = args
        pad.avatar = avatar
        pad.delayDelete = DelayDelete.DelayDelete(avatar, 'getAvatarDetails')
        self.__queryAvatarMap[avatar.doId] = pad
        self.__sendGetAvatarDetails(avatar.doId)

    def cancelAvatarDetailsRequest(self, avatar):
        avId = avatar.doId
        if avId in self.__queryAvatarMap:
            pad = self.__queryAvatarMap.pop(avId)
            pad.delayDelete.destroy()

    def __sendGetAvatarDetails(self, avId):
        self.ttiFriendsManager.d_getAvatarDetails(avId)

    def n_handleGetAvatarDetailsResp(self, avId, fields):
        self.notify.info('Query reponse for avId %d' % avId)
        try:
            pad = self.__queryAvatarMap[avId]
        except:
            self.notify.warning('Received unexpected or outdated details for avatar %d.' % avId)
            return

        del self.__queryAvatarMap[avId]
        gotData = 0

        dclassName = pad.args[0]
        dclass = self.dclassesByName[dclassName]
        #pad.avatar.updateAllRequiredFields(dclass, fields)

        # This is a much saner way to load avatar details, and is also
        # dynamic. This means we aren't restricted in what we pass.
        # Due to Python's random ordering of dictionaries, we have to pass
        # a list containing a list of the field and value. For example:
        # To set the hp and maxHp of an avatar, my fields list would be
        # fields = [['setHp', 15], ['setMaxHp', 15]]

        for currentField in fields:
            getattr(pad.avatar, currentField[0])(currentField[1])

        gotData = 1


        if isinstance(pad.func, types.StringType):
            messenger.send(pad.func, list((gotData, pad.avatar) + pad.args))
        else:
            apply(pad.func, (gotData, pad.avatar) + pad.args)

        pad.delayDelete.destroy()

    def handleGetAvatarDetailsResp(self, di):
        avId = di.getUint32()
        returnCode = di.getUint8()
        self.notify.info('Got query response for avatar %d, code = %d.' % (avId, returnCode))
        try:
            pad = self.__queryAvatarMap[avId]
        except:
            self.notify.warning('Received unexpected or outdated details for avatar %d.' % avId)
            return

        del self.__queryAvatarMap[avId]
        gotData = 0
        if returnCode != 0:
            self.notify.warning('No information available for avatar %d.' % avId)
        else:
            dclassName = pad.args[0]
            dclass = self.dclassesByName[dclassName]
            pad.avatar.updateAllRequiredFields(dclass, di)
            gotData = 1
        if isinstance(pad.func, types.StringType):
            messenger.send(pad.func, list((gotData, pad.avatar) + pad.args))
        else:
            apply(pad.func, (gotData, pad.avatar) + pad.args)
        pad.delayDelete.destroy()

    def enterPlayingGame(self, *args, **kArgs):
        OTPClientRepository.OTPClientRepository.enterPlayingGame(self, *args, **kArgs)
        self.gameFSM.request('waitOnEnterResponses', [None,
         base.localAvatar.defaultZone,
         base.localAvatar.defaultZone,
         -1])
        self._userLoggingOut = False
        if not self.streetSign:
            self.streetSign = StreetSign.StreetSign()
        return

    def exitPlayingGame(self):
        ivalMgr.interrupt()
        if self.objectManager != None:
            self.objectManager.destroy()
            self.objectManager = None
        ToontownFriendSecret.unloadFriendSecret()
        FriendsListPanel.unloadFriendsList()
        messenger.send('cancelFriendInvitation')
        base.removeGlitchMessage()
        taskMgr.remove('avatarRequestQueueTask')
        OTPClientRepository.OTPClientRepository.exitPlayingGame(self)
        if hasattr(base, 'localAvatar'):
            camera.reparentTo(render)
            camera.setPos(0, 0, 0)
            camera.setHpr(0, 0, 0)
            del self.doId2do[base.localAvatar.getDoId()]
            if base.localAvatar.getDelayDeleteCount() != 0:
                self.notify.error('could not delete localAvatar, delayDeletes=%s' % (base.localAvatar.getDelayDeleteNames(),))
            base.localAvatar.deleteOrDelay()
            base.localAvatar.detectLeaks()
            NametagGlobals.setMe(base.cam)
            del base.localAvatar
            del __builtins__['localAvatar']
        base.localAvatarStyle = None
        base.localAvatarName = None
        loader.abortBulkLoad()
        base.transitions.noTransitions()
        if self._userLoggingOut:
            self.detectLeaks(okTasks=[], okEvents=['destroy-ToontownLoadingScreenTitle', 'destroy-ToontownLoadingScreenTip', 'destroy-ToontownLoadingScreenWaitBar'])
        return

    def enterGameOff(self):
        OTPClientRepository.OTPClientRepository.enterGameOff(self)

    def enterWaitOnEnterResponses(self, shardId, hoodId, zoneId, avId):
        self.resetDeletedSubShardDoIds()
        OTPClientRepository.OTPClientRepository.enterWaitOnEnterResponses(self, shardId, hoodId, zoneId, avId)

    def enterSkipTutorialRequest(self, hoodId, zoneId, avId):
        self.handlerArgs = {'hoodId': hoodId,
         'zoneId': zoneId,
         'avId': avId}
        self.__requestSkipTutorial(hoodId, zoneId, avId)

    def __requestSkipTutorial(self, hoodId, zoneId, avId):
        self.notify.debug('requesting skip tutorial')
        self.acceptOnce('skipTutorialAnswered', self.__handleSkipTutorialAnswered, [hoodId, zoneId, avId])
        messenger.send('requestSkipTutorial')
        self.waitForDatabaseTimeout(requestName='RequestSkipTutorial')

    def __handleSkipTutorialAnswered(self, hoodId, zoneId, avId, allOk):
        if allOk:
            hoodId = self.handlerArgs['hoodId']
            zoneId = self.handlerArgs['zoneId']
            avId = self.handlerArgs['avId']
            self.gameFSM.request('playGame', [hoodId, zoneId, avId])
        else:
            self.notify.warning('allOk is false on skip tutorial, forcing the tutorial.')
            self.gameFSM.request('tutorialQuestion', [hoodId, zoneId, avId])

    def exitSkipTutorialRequest(self):
        self.cleanupWaitingForDatabase()
        self.handler = None
        self.handlerArgs = None
        self.ignore('skipTutorialAnswered')
        return

    def enterTutorialQuestion(self, hoodId, zoneId, avId):
        self.__requestTutorial(hoodId, zoneId, avId)

    def __requestTutorial(self, hoodId, zoneId, avId):
        self.notify.debug('requesting tutorial')
        self.acceptOnce('startTutorial', self.__handleStartTutorial, [avId])
        messenger.send('requestTutorial')
        self.waitForDatabaseTimeout(requestName='RequestTutorial')

    def __handleStartTutorial(self, avId, zoneId):
        self.gameFSM.request('playGame', [Tutorial, zoneId, avId])

    def exitTutorialQuestion(self):
        self.cleanupWaitingForDatabase()
        self.handler = None
        self.handlerArgs = None
        self.ignore('startTutorial')
        taskMgr.remove('waitingForTutorial')
        return

    def enterSwitchShards(self, shardId, hoodId, zoneId, avId):
        OTPClientRepository.OTPClientRepository.enterSwitchShards(self, shardId, hoodId, zoneId, avId)
        self.handler = self.handleCloseShard

    def exitSwitchShards(self):
        OTPClientRepository.OTPClientRepository.exitSwitchShards(self)
        self.ignore(ToontownClientRepository.ClearInterestDoneEvent)
        self.handler = None
        return

    def enterCloseShard(self, loginState = None):
        OTPClientRepository.OTPClientRepository.enterCloseShard(self, loginState)
        self.handler = self.handleCloseShard
        self._removeLocalAvFromStateServer()

    def handleCloseShard(self, msgType, di):
        if msgType == CLIENT_ENTER_OBJECT_REQUIRED:
            di2 = PyDatagramIterator(di)
            parentId = di2.getUint32()
            if self._doIdIsOnCurrentShard(parentId):
                return
        elif msgType == CLIENT_ENTER_OBJECT_REQUIRED_OTHER:
            di2 = PyDatagramIterator(di)
            parentId = di2.getUint32()
            if self._doIdIsOnCurrentShard(parentId):
                return
        elif msgType == CLIENT_OBJECT_SET_FIELD:
            di2 = PyDatagramIterator(di)
            doId = di2.getUint32()
            if self._doIdIsOnCurrentShard(doId):
                return
        self.handleMessageType(msgType, di)

    def _logFailedDisable(self, doId, ownerView):
        if doId not in self.doId2do and doId in self._deletedSubShardDoIds:
            return
        OTPClientRepository.OTPClientRepository._logFailedDisable(self, doId, ownerView)

    def exitCloseShard(self):
        OTPClientRepository.OTPClientRepository.exitCloseShard(self)
        self.ignore(ToontownClientRepository.ClearInterestDoneEvent)
        self.handler = None
        return

    def isShardInterestOpen(self):
        return self.old_setzone_interest_handle is not None or self.uberZoneInterest is not None

    def resetDeletedSubShardDoIds(self):
        self._deletedSubShardDoIds.clear()

    def dumpAllSubShardObjects(self):
        if self.KeepSubShardObjects:
            return
        isNotLive = not base.cr.isLive()
        if isNotLive:
            try:
                localAvatar
            except:
                self.notify.info('dumpAllSubShardObjects')
            else:
                self.notify.info('dumpAllSubShardObjects: defaultShard is %s' % localAvatar.defaultShard)

            ignoredClasses = ('MagicWordManager', 'TimeManager', 'DistributedDistrict', 'FriendManager', 'NewsManager', 'ToontownMagicWordManager', 'WelcomeValleyManager', 'DistributedTrophyMgr', 'CatalogManager', 'DistributedBankMgr', 'EstateManager', 'RaceManager', 'SafeZoneManager', 'DeleteManager', 'TutorialManager', 'ToontownDistrict', 'DistributedDeliveryManager', 'DistributedPartyManager', 'AvatarFriendsManager', 'InGameNewsMgr', 'WhitelistMgr', 'TTCodeRedemptionMgr')
        messenger.send('clientCleanup')
        for avId, pad in self.__queryAvatarMap.items():
            pad.delayDelete.destroy()

        self.__queryAvatarMap = {}
        delayDeleted = []
        doIds = self.doId2do.keys()
        for doId in doIds:
            obj = self.doId2do[doId]
            if isNotLive:
                ignoredClass = obj.__class__.__name__ in ignoredClasses
                if not ignoredClass and obj.parentId != localAvatar.defaultShard:
                    self.notify.info('dumpAllSubShardObjects: %s %s parent %s is not defaultShard' % (obj.__class__.__name__, obj.doId, obj.parentId))
            if obj.parentId == localAvatar.defaultShard and obj is not localAvatar:
                if obj.neverDisable:
                    if isNotLive:
                        if not ignoredClass:
                            self.notify.warning('dumpAllSubShardObjects: neverDisable set for %s %s' % (obj.__class__.__name__, obj.doId))
                else:
                    self.deleteObject(doId)
                    self._deletedSubShardDoIds.add(doId)
                    if obj.getDelayDeleteCount() != 0:
                        delayDeleted.append(obj)

        delayDeleteLeaks = []
        for obj in delayDeleted:
            if obj.getDelayDeleteCount() != 0:
                delayDeleteLeaks.append(obj)

        if len(delayDeleteLeaks):
            s = 'dumpAllSubShardObjects:'
            for obj in delayDeleteLeaks:
                s += '\n  could not delete %s (%s), delayDeletes=%s' % (safeRepr(obj), itype(obj), obj.getDelayDeleteNames())

            self.notify.error(s)
        if isNotLive:
            self.notify.info('dumpAllSubShardObjects: doIds left: %s' % self.doId2do.keys())

    def _removeCurrentShardInterest(self, callback):
        if self.old_setzone_interest_handle is None:
            self.notify.warning('removeToontownShardInterest: no shard interest open')
            callback()
            return
        self.acceptOnce(ToontownClientRepository.ClearInterestDoneEvent, Functor(self._tcrRemoveUberZoneInterest, callback))
        self._removeEmulatedSetZone(ToontownClientRepository.ClearInterestDoneEvent)
        return

    def _tcrRemoveUberZoneInterest(self, callback):
        self.acceptOnce(ToontownClientRepository.ClearInterestDoneEvent, Functor(self._tcrRemoveShardInterestDone, callback))
        self.removeInterest(self.uberZoneInterest, ToontownClientRepository.ClearInterestDoneEvent)

    def _tcrRemoveShardInterestDone(self, callback):
        self.uberZoneInterest = None
        callback()
        return

    def _doIdIsOnCurrentShard(self, doId):
        if doId == base.localAvatar.defaultShard:
            return True
        do = self.getDo(doId)
        if do:
            if do.parentId == base.localAvatar.defaultShard:
                return True
        return False

    def _wantShardListComplete(self):
        print self.activeDistrictMap
        if self._shardsAreReady():
            self.acceptOnce(ToontownDistrictStats.EventName(), self.shardDetailStatsComplete)
            ToontownDistrictStats.refresh()
        else:
            self.loginFSM.request('noShards')

    def shardDetailStatsComplete(self):
        self.loginFSM.request('waitForAvatarList')

    def exitWaitForShardList(self):
        self.ignore(ToontownDistrictStats.EventName())
        OTPClientRepository.OTPClientRepository.exitWaitForShardList(self)

    def fillUpFriendsMap(self):
        if self.isFriendsMapComplete():
            return 1
        if not self.friendsMapPending and not self.friendsListError:
            self.notify.warning('Friends list stale; fetching new list.')
            self.sendGetFriendsListRequest()
        return 0

    def isFriend(self, doId):
        for friendId, flags in base.localAvatar.friendsList:
            if friendId == doId:
                self.identifyFriend(doId)
                return 1

        return 0

    def isAvatarFriend(self, doId):
        for friendId, flags in base.localAvatar.friendsList:
            if friendId == doId:
                self.identifyFriend(doId)
                return 1

        return 0

    def getFriendFlags(self, doId):
        for friendId, flags in base.localAvatar.friendsList:
            if friendId == doId:
                return flags

        return 0

    def isFriendOnline(self, doId):
        return doId in self.friendsOnline

    def addAvatarToFriendsList(self, avatar):
        self.friendsMap[avatar.doId] = avatar

    def identifyFriend(self, doId, source = None):
        if doId in self.friendsMap:
            teleportNotify.debug('friend %s in friendsMap' % doId)
            return self.friendsMap[doId]
        avatar = None
        if doId in self.doId2do:
            teleportNotify.debug('found friend %s in doId2do' % doId)
            avatar = self.doId2do[doId]
        elif self.cache.contains(doId):
            teleportNotify.debug('found friend %s in cache' % doId)
            avatar = self.cache.dict[doId]
        elif self.playerFriendsManager.getAvHandleFromId(doId):
            teleportNotify.debug('found friend %s in playerFriendsManager' % doId)
            avatar = base.cr.playerFriendsManager.getAvHandleFromId(doId)
        else:
            self.notify.warning("Don't know who friend %s is." % doId)
            return
        if not ((isinstance(avatar, DistributedToon.DistributedToon) and avatar.__class__ is DistributedToon.DistributedToon) or isinstance(avatar, DistributedPet.DistributedPet)):
            self.notify.warning('friendsNotify%s: invalid friend object %s' % (choice(source, '(%s)' % source, ''), doId))
            return
        if base.wantPets:
            if avatar.isPet():
                if avatar.bFake:
                    handle = PetHandle.PetHandle(avatar)
                else:
                    handle = avatar
            else:
                handle = FriendHandle.FriendHandle(doId, avatar.getName(), avatar.style, avatar.getPetId())
        else:
            handle = FriendHandle.FriendHandle(doId, avatar.getName(), avatar.style, '')
        teleportNotify.debug('adding %s to friendsMap' % doId)
        self.friendsMap[doId] = handle
        return handle

    def identifyPlayer(self, pId):
        return base.cr.playerFriendsManager.getFriendInfo(pId)

    def identifyAvatar(self, doId):
        if doId in self.doId2do:
            return self.doId2do[doId]
        else:
            return self.identifyFriend(doId)

    def isFriendsMapComplete(self):
        for friendId, flags in base.localAvatar.friendsList:
            if self.identifyFriend(friendId) == None:
                return 0

        if base.wantPets and base.localAvatar.hasPet():
            if base.localAvatar.getPetId() not in self.friendsMap:
                return 0
        return 1

    def removeFriend(self, avatarId):
        self.ttiFriendsManager.d_removeFriend(avatarId)

    def clearFriendState(self):
        self.friendsMap = {}
        self.friendsOnline = {}
        self.friendsMapPending = 0
        self.friendsListError = 0

    def sendGetFriendsListRequest(self):
        self.friendsMapPending = 1
        self.friendsListError = 0
        self.ttiFriendsManager.d_requestFriendsList()

    def cleanPetsFromFriendsMap(self):
        for objId, obj in self.friendsMap.items():
            from toontown.pets import DistributedPet
            if isinstance(obj, DistributedPet.DistributedPet):
                print 'Removing %s reference from the friendsMap' % obj.getName()
                del self.friendsMap[objId]

    def removePetFromFriendsMap(self):
        doId = base.localAvatar.getPetId()
        if doId and doId in self.friendsMap:
            del self.friendsMap[doId]

    def addPetToFriendsMap(self, callback = None):
        doId = base.localAvatar.getPetId()
        if doId not in self.friendsMap:
            if callback:
                callback()
            return

        def petDetailsCallback(petAvatar):
            handle = PetHandle.PetHandle(petAvatar)
            self.friendsMap[doId] = handle
            petAvatar.disable()
            petAvatar.delete()
            if callback:
                callback()
            if self._proactiveLeakChecks:
                petAvatar.detectLeaks()

        PetDetail.PetDetail(doId, petDetailsCallback)

    def handleGetFriendsList(self, resp):
        print len(resp)
        for toon in resp:
            doId = toon[0]
            name = toon[1]
            dnaString = toon[2]
            dna = ToonDNA.ToonDNA()
            dna.makeFromNetString(dnaString)
            petId = toon[3]
            handle = FriendHandle.FriendHandle(doId, name, dna, petId)
            self.friendsMap[doId] = handle
            if doId in self.friendsOnline:
                self.friendsOnline[doId] = handle
            if doId in self.friendPendingChatSettings:
                self.notify.debug('calling setCommonAndWL %s' % str(self.friendPendingChatSettings[doId]))
                handle.setCommonAndWhitelistChatFlags(*self.friendPendingChatSettings[doId])

        if base.wantPets and base.localAvatar.hasPet():

            def handleAddedPet():
                self.friendsMapPending = 0
                messenger.send('friendsMapComplete')

            self.addPetToFriendsMap(handleAddedPet)
            return
        self.friendsMapPending = 0
        messenger.send('friendsMapComplete')

    def handleGetFriendsListExtended(self, resp):
        for toon in resp:
            abort = 0
            doId = toon[0]
            name = toon[1]
            if name == '':
                abort = 1
            dnaString = toon[2]
            if dnaString == '':
                abort = 1
            else:
                dna = ToonDNA.ToonDNA()
                dna.makeFromNetString(dnaString)
            petId = toon[3]
            if not abort:
                handle = FriendHandle.FriendHandle(doId, name, dna, petId)
                avatarHandleList.append(handle)

        if avatarHandleList:
            messenger.send('gotExtraFriendHandles', [avatarHandleList])

    def handleFriendOnline(self, doId, commonChatFlags, whitelistChatFlags):
        self.notify.debug('Friend %d now online. common=%d whitelist=%d' % (doId, commonChatFlags, whitelistChatFlags))
        if doId not in self.friendsOnline:
            self.friendsOnline[doId] = self.identifyFriend(doId)
            messenger.send('friendOnline', [doId, commonChatFlags, whitelistChatFlags])
            if not self.friendsOnline[doId]:
                self.friendPendingChatSettings[doId] = (commonChatFlags, whitelistChatFlags)

    def handleFriendOffline(self, doId):
        self.notify.debug('Friend %d now offline.' % doId)
        try:
            del self.friendsOnline[doId]
            messenger.send('friendOffline', [doId])
        except:
            pass

    def handleGenerateWithRequiredOtherOwner(self, di):
        # Toontown only makes use of OwnerViews for LocalToon.
        if self.loginFSM.getCurrentState().getName() == 'waitForSetAvatarResponse':
            doId = di.getUint32()
            parentId = di.getUint32()
            zoneId = di.getUint32()
            dclassId = di.getUint16()
            self.handleAvatarResponseMsg(doId, di)

    def getFirstBattle(self):
        from toontown.battle import DistributedBattleBase
        for dobj in self.doId2do.values():
            if isinstance(dobj, DistributedBattleBase.DistributedBattleBase):
                return dobj

    def forbidCheesyEffects(self, forbid):
        wasAllowed = self.__forbidCheesyEffects != 0
        if forbid:
            self.__forbidCheesyEffects += 1
        else:
            self.__forbidCheesyEffects -= 1
        isAllowed = self.__forbidCheesyEffects != 0
        if wasAllowed != isAllowed:
            for av in Avatar.Avatar.ActiveAvatars:
                if hasattr(av, 'reconsiderCheesyEffect'):
                    av.reconsiderCheesyEffect()

            base.localAvatar.reconsiderCheesyEffect()

    def areCheesyEffectsAllowed(self):
        return self.__forbidCheesyEffects == 0

    def getNextSetZoneDoneEvent(self):
        return '%s-%s' % (ToontownClientRepository.EmuSetZoneDoneEvent, self.setZonesEmulated + 1)

    def getLastSetZoneDoneEvent(self):
        return '%s-%s' % (ToontownClientRepository.EmuSetZoneDoneEvent, self.setZonesEmulated)

    def getQuietZoneLeftEvent(self):
        return 'leftQuietZone-%s' % (id(self),)

    def sendSetZoneMsg(self, zoneId, visibleZoneList = None):
        event = self.getNextSetZoneDoneEvent()
        self.setZonesEmulated += 1
        parentId = base.localAvatar.defaultShard
        self.sendSetLocation(base.localAvatar.doId, parentId, zoneId)
        localAvatar.setLocation(parentId, zoneId)
        interestZones = zoneId
        if visibleZoneList is not None:
            interestZones = visibleZoneList
        self._addInterestOpToQueue(ToontownClientRepository.SetInterest, [parentId, interestZones, 'OldSetZoneEmulator'], event)
        return

    def resetInterestStateForConnectionLoss(self):
        OTPClientRepository.OTPClientRepository.resetInterestStateForConnectionLoss(self)
        self.old_setzone_interest_handle = None
        self.setZoneQueue.clear()
        return

    def _removeEmulatedSetZone(self, doneEvent):
        self._addInterestOpToQueue(ToontownClientRepository.ClearInterest, None, doneEvent)
        return

    def _addInterestOpToQueue(self, op, args, event):
        self.setZoneQueue.push([op, args, event])
        if len(self.setZoneQueue) == 1:
            self._sendNextSetZone()

    def _sendNextSetZone(self):
        op, args, event = self.setZoneQueue.top()
        if op == ToontownClientRepository.SetInterest:
            parentId, interestZones, name = args
            if self.old_setzone_interest_handle == None:
                self.old_setzone_interest_handle = self.addInterest(parentId, interestZones, name, ToontownClientRepository.SetZoneDoneEvent)
            else:
                self.alterInterest(self.old_setzone_interest_handle, parentId, interestZones, name, ToontownClientRepository.SetZoneDoneEvent)
        elif op == ToontownClientRepository.ClearInterest:
            self.removeInterest(self.old_setzone_interest_handle, ToontownClientRepository.SetZoneDoneEvent)
            self.old_setzone_interest_handle = None
        else:
            self.notify.error('unknown setZone op: %s' % op)
        return

    def _handleEmuSetZoneDone(self):
        op, args, event = self.setZoneQueue.pop()
        queueIsEmpty = self.setZoneQueue.isEmpty()
        if event is not None:
            if not base.killInterestResponse:
                messenger.send(event)
            elif not hasattr(self, '_dontSendSetZoneDone'):
                import random
                if random.random() < 0.05:
                    self._dontSendSetZoneDone = True
                else:
                    messenger.send(event)
        if not queueIsEmpty:
            self._sendNextSetZone()
        return

    def _isPlayerDclass(self, dclass):
        return dclass == self._playerAvDclass

    def _isValidPlayerLocation(self, parentId, zoneId):
        if not self.distributedDistrict:
            return False
        if parentId != self.distributedDistrict.doId:
            return False
        if parentId == self.distributedDistrict.doId and zoneId == OTPGlobals.UberZone:
            return False
        return True

    def sendQuietZoneRequest(self):
        self.sendSetZoneMsg(OTPGlobals.QuietZone, [])

    def handleQuietZoneGenerateWithRequired(self, di):
        doId = di.getUint32()
        parentId = di.getUint32()
        zoneId = di.getUint32()
        classId = di.getUint16()
        dclass = self.dclassesByNumber[classId]
        if dclass.getClassDef().neverDisable:
            dclass.startGenerate()
            distObj = self.generateWithRequiredFields(dclass, doId, di, parentId, zoneId)
            dclass.stopGenerate()

    def handleQuietZoneGenerateWithRequiredOther(self, di):
        doId = di.getUint32()
        parentId = di.getUint32()
        zoneId = di.getUint32()
        classId = di.getUint16()
        dclass = self.dclassesByNumber[classId]
        if dclass.getClassDef().neverDisable:
            dclass.startGenerate()
            distObj = self.generateWithRequiredOtherFields(dclass, doId, di, parentId, zoneId)
            dclass.stopGenerate()

    def handleQuietZoneUpdateField(self, di):
        di2 = DatagramIterator(di)
        doId = di2.getUint32()
        if doId in self.deferredDoIds:
            args, deferrable, dg0, updates = self.deferredDoIds[doId]
            dclass = args[2]
            if not dclass.getClassDef().neverDisable:
                return
        else:
            do = self.getDo(doId)
            if do:
                if not do.neverDisable:
                    return
        OTPClientRepository.OTPClientRepository.handleUpdateField(self, di)

    def handleDelete(self, di):
        doId = di.getUint32()
        self.deleteObject(doId)

    def deleteObject(self, doId, ownerView = False):
        if doId in self.doId2do:
            obj = self.doId2do[doId]
            del self.doId2do[doId]
            obj.deleteOrDelay()
            if obj.getDelayDeleteCount() <= 0:
                obj.detectLeaks()
        elif self.cache.contains(doId):
            self.cache.delete(doId)
        else:
            self.notify.warning('Asked to delete non-existent DistObj ' + str(doId))

    def _abandonShard(self):
        for doId, obj in self.doId2do.items():
            if obj.parentId == localAvatar.defaultShard and obj is not localAvatar:
                self.deleteObject(doId)

    def askAvatarKnown(self, avId):
        if not hasattr(base, 'localAvatar'):
            return 0
        for friendPair in base.localAvatar.friendsList:
            if friendPair[0] == avId:
                return 1

        return 0

    def requestAvatarInfo(self, avId):
        if avId == 0:
            return
        self.ttiFriendsManager.d_requestAvatarInfo([avId])

    def queueRequestAvatarInfo(self, avId):
        removeTask = 0
        if not hasattr(self, 'avatarInfoRequests'):
            self.avatarInfoRequests = []
        if self.avatarInfoRequests:
            taskMgr.remove('avatarRequestQueueTask')
        if avId not in self.avatarInfoRequests:
            self.avatarInfoRequests.append(avId)
        taskMgr.doMethodLater(0.1, self.sendAvatarInfoRequests, 'avatarRequestQueueTask')

    def sendAvatarInfoRequests(self, task = None):
        if not hasattr(self, 'avatarInfoRequests'):
            return
        if len(self.avatarInfoRequests) == 0:
            return
        self.ttiFriendsManager.d_requestAvatarInfo(self.avatarInfoRequests)
