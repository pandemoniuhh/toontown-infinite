from direct.actor import Actor
from direct.directnotify.DirectNotifyGlobal import *
from direct.distributed import ClockDelta
from direct.interval.IntervalGlobal import *
from toontown.util import PythonUtil
from direct.showutil import Rope
from direct.task import Task
from panda3d.core import *

import DistributedFurnitureItem
import PhoneGlobals
from toontown.catalog import CatalogItem
from toontown.catalog.CatalogGUI import CatalogGUI
from toontown.catalog.CatalogItemListGUI import CatalogItemListGUI
from toontown.catalog.CatalogItemSorter import CatalogItemSorter
from toontown.quest import Quests
from toontown.toonbase import TTLocalizer
from toontown.toonbase import ToontownGlobals
from toontown.toontowngui import TTDialog


class DistributedPhone(DistributedFurnitureItem.DistributedFurnitureItem):
    notify = directNotify.newCategory('DistributedPhone')
    movieDelay = 0.5

    def __init__(self, cr):
        DistributedFurnitureItem.DistributedFurnitureItem.__init__(self, cr)
        self.lastAvId = 0
        self.hasLocalAvatar = 0
        self.lastTime = 0
        self.initialScale = None
        self.usedInitialScale = 0
        self.toonScale = None
        self.phoneGui = None
        self.phoneDialog = None
        self.model = None
        self.cord = None
        self.receiverGeom = None
        self.receiverJoint = None
        self.phoneSphereEvent = 'phoneSphere'
        self.phoneSphereEnterEvent = 'enter' + self.phoneSphereEvent
        self.phoneGuiDoneEvent = 'phoneGuiDone'
        self.pickupMovieDoneEvent = 'phonePickupDone'
        self.numHouseItems = None
        self.interval = None
        self.intervalAvatar = None
        self.phoneInUse = 0
        self.origToonHpr = None

    def announceGenerate(self):
        self.notify.debug('announceGenerate')
        DistributedFurnitureItem.DistributedFurnitureItem.announceGenerate(self)
        self.accept(self.phoneSphereEnterEvent, self.__handleEnterSphere)
        self.load()
        taskMgr.doMethodLater(6, self.ringIfHasPhoneQuest, self.uniqueName('ringDoLater'))

    def loadModel(self):
        self.model = Actor.Actor('phase_5.5/models/estate/prop_phone-mod', {'SS_phoneOut': 'phase_5.5/models/estate/prop_phone-SS_phoneOut',
         'SS_takePhone': 'phase_5.5/models/estate/prop_phone-SS_takePhone',
         'SS_phoneNeutral': 'phase_5.5/models/estate/prop_phone-SS_phoneNeutral',
         'SS_phoneBack': 'phase_5.5/models/estate/prop_phone-SS_phoneBack',
         'SM_phoneOut': 'phase_5.5/models/estate/prop_phone-SM_phoneOut',
         'SM_takePhone': 'phase_5.5/models/estate/prop_phone-SM_takePhone',
         'SM_phoneNeutral': 'phase_5.5/models/estate/prop_phone-SM_phoneNeutral',
         'SM_phoneBack': 'phase_5.5/models/estate/prop_phone-SM_phoneBack',
         'SL_phoneOut': 'phase_5.5/models/estate/prop_phone-SL_phoneOut',
         'SL_takePhone': 'phase_5.5/models/estate/prop_phone-SL_takePhone',
         'SL_phoneNeutral': 'phase_5.5/models/estate/prop_phone-SL_phoneNeutral',
         'SL_phoneBack': 'phase_5.5/models/estate/prop_phone-SL_phoneBack',
         'MS_phoneOut': 'phase_5.5/models/estate/prop_phone-MS_phoneOut',
         'MS_takePhone': 'phase_5.5/models/estate/prop_phone-MS_takePhone',
         'MS_phoneNeutral': 'phase_5.5/models/estate/prop_phone-MS_phoneNeutral',
         'MS_phoneBack': 'phase_5.5/models/estate/prop_phone-MS_phoneBack',
         'MM_phoneOut': 'phase_5.5/models/estate/prop_phone-MM_phoneOut',
         'MM_takePhone': 'phase_5.5/models/estate/prop_phone-MM_takePhone',
         'MM_phoneNeutral': 'phase_5.5/models/estate/prop_phone-MM_phoneNeutral',
         'MM_phoneBack': 'phase_5.5/models/estate/prop_phone-MM_phoneBack',
         'ML_phoneOut': 'phase_5.5/models/estate/prop_phone-ML_phoneOut',
         'ML_takePhone': 'phase_5.5/models/estate/prop_phone-ML_takePhone',
         'ML_phoneNeutral': 'phase_5.5/models/estate/prop_phone-ML_phoneNeutral',
         'ML_phoneBack': 'phase_5.5/models/estate/prop_phone-ML_phoneBack',
         'LS_phoneOut': 'phase_5.5/models/estate/prop_phone-LS_phoneOut',
         'LS_takePhone': 'phase_5.5/models/estate/prop_phone-LS_takePhone',
         'LS_phoneNeutral': 'phase_5.5/models/estate/prop_phone-LS_phoneNeutral',
         'LS_phoneBack': 'phase_5.5/models/estate/prop_phone-LS_phoneBack',
         'LM_phoneOut': 'phase_5.5/models/estate/prop_phone-LM_phoneOut',
         'LM_takePhone': 'phase_5.5/models/estate/prop_phone-LM_takePhone',
         'LM_phoneNeutral': 'phase_5.5/models/estate/prop_phone-LM_phoneNeutral',
         'LM_phoneBack': 'phase_5.5/models/estate/prop_phone-LM_phoneBack',
         'LL_phoneOut': 'phase_5.5/models/estate/prop_phone-LL_phoneOut',
         'LL_takePhone': 'phase_5.5/models/estate/prop_phone-LL_takePhone',
         'LL_phoneNeutral': 'phase_5.5/models/estate/prop_phone-LL_phoneNeutral',
         'LL_phoneBack': 'phase_5.5/models/estate/prop_phone-LL_phoneBack'})
        self.model.pose('SS_phoneOut', 0)
        self.receiverJoint = self.model.find('**/joint_receiver')
        self.receiverGeom = self.receiverJoint.getChild(0)
        mount = loader.loadModel('phase_5.5/models/estate/phoneMount-mod')
        mount.setTransparency(0, 1)
        self.model.reparentTo(mount)
        self.ringSfx = loader.loadSfx('phase_3.5/audio/sfx/telephone_ring.ogg')
        self.handleSfx = loader.loadSfx('phase_5.5/audio/sfx/telephone_handle2.ogg')
        self.hangUpSfx = loader.loadSfx('phase_5.5/audio/sfx/telephone_hang_up.ogg')
        self.pickUpSfx = loader.loadSfx('phase_5.5/audio/sfx/telephone_pickup1.ogg')
        if self.initialScale:
            mount.setScale(*self.initialScale)
            self.usedInitialScale = 1
        phoneSphere = CollisionSphere(0, -0.66, 0, 0.2)
        phoneSphere.setTangible(0)
        phoneSphereNode = CollisionNode(self.phoneSphereEvent)
        phoneSphereNode.setIntoCollideMask(ToontownGlobals.WallBitmask)
        phoneSphereNode.addSolid(phoneSphere)
        mount.attachNewNode(phoneSphereNode)
        if not self.model.find('**/CurveNode7').isEmpty():
            self.setupCord()
        return mount

    def setupCamera(self, mode):
        camera.wrtReparentTo(render)
        if mode == PhoneGlobals.PHONE_MOVIE_PICKUP:
            camera.posQuatInterval(1, (4, -4, base.localAvatar.getHeight()- 0.5), (35, -8, 0), other=base.localAvatar, blendType='easeOut').start()

    def setupCord(self):
        if self.cord:
            self.cord.detachNode()
            self.cord = None
        self.cord = Rope.Rope(self.uniqueName('phoneCord'))
        self.cord.setColor(0, 0, 0, 1)
        self.cord.setup(4, ((self.receiverGeom, (0, 0, 0)),
         (self.model.find('**/joint_curveNode1'), (0, 0, 0)),
         (self.model.find('**/joint_curveNode2'), (0, 0, 0)),
         (self.model.find('**/joint_curveNode3'), (0, 0, 0)),
         (self.model.find('**/joint_curveNode4'), (0, 0, 0)),
         (self.model.find('**/joint_curveNode5'), (0, 0, 0)),
         (self.model.find('**/joint_curveNode6'), (0, 0, 0)),
         (self.model.find('**/CurveNode7'), (0, 0, 0))))
        self.cord.reparentTo(self.model)
        self.cord.node().setBounds(BoundingSphere(Point3(-1.0, -3.2, 2.6), 2.0))

    def disable(self):
        self.notify.debug('disable')
        taskMgr.remove(self.uniqueName('ringDoLater'))
        self.clearInterval()
        if self.phoneGui:
            self.phoneGui.hide()
            self.phoneGui.unload()
            self.phoneGui = None
        if self.phoneDialog:
            self.phoneDialog.cleanup()
            self.phoneDialog = None
        self.__receiverToPhone()
        if self.hasLocalAvatar:
            self.freeAvatar()
        self.ignoreAll()
        DistributedFurnitureItem.DistributedFurnitureItem.disable(self)

    def delete(self):
        self.notify.debug('delete')
        self.model.cleanup()
        DistributedFurnitureItem.DistributedFurnitureItem.delete(self)

    def setInitialScale(self, sx, sy, sz):
        self.initialScale = (sx, sy, sz)
        if not self.usedInitialScale and self.model:
            self.setScale(*self.initialScale)
            self.usedInitialScale = 1

    def __handleEnterSphere(self, collEntry):
        if self.smoothStarted:
            return
        if base.localAvatar.doId == self.lastAvId and globalClock.getFrameTime() <= self.lastTime + 0.5:
            self.notify.debug('Ignoring duplicate entry for avatar.')
            return
        if self.hasLocalAvatar:
            self.freeAvatar()
        if hasattr(base, 'wantPets') and base.wantPets:
            base.localAvatar.lookupPetDNA()
        self.notify.debug('Entering Phone Sphere....')
        taskMgr.remove(self.uniqueName('ringDoLater'))
        self.ignore(self.phoneSphereEnterEvent)
        self.cr.playGame.getPlace().detectedPhoneCollision()
        self.hasLocalAvatar = 1
        self.sendUpdate('avatarEnter')

    def __handlePhoneDone(self):
        self.sendUpdate('avatarExit')
        self.ignore(self.phoneGuiDoneEvent)
        self.phoneGui = None

    def freeAvatar(self):
        if self.hasLocalAvatar:
            base.localAvatar.speed = 0
            taskMgr.remove(self.uniqueName('lerpCamera'))
            base.localAvatar.posCamera(0, 0)
            if base.cr.playGame.place != None:
                base.cr.playGame.getPlace().setState('walk')
            self.hasLocalAvatar = 0
        self.ignore(self.pickupMovieDoneEvent)
        self.accept(self.phoneSphereEnterEvent, self.__handleEnterSphere)
        self.stopSmooth()
        self.lastTime = globalClock.getFrameTime()

    def setLimits(self, numHouseItems):
        self.numHouseItems = numHouseItems

    def setMovie(self, mode, avId, timestamp):
        elapsed = ClockDelta.globalClockDelta.localElapsedTime(timestamp, bits=32)
        elapsed = max(elapsed - self.movieDelay, 0)
        self.ignore(self.pickupMovieDoneEvent)
        if avId != 0:
            self.lastAvId = avId
        self.lastTime = globalClock.getFrameTime()
        isLocalToon = avId == base.localAvatar.doId
        avatar = self.cr.doId2do.get(avId)
        if mode == PhoneGlobals.PHONE_MOVIE_CLEAR:
            if self.phoneInUse:
                self.clearInterval()
            self.numHouseItems = None
            self.phoneInUse = 0
        elif mode == PhoneGlobals.PHONE_MOVIE_EMPTY:
            if isLocalToon:
                self.phoneDialog = TTDialog.TTDialog(dialogName='PhoneEmpty', style=TTDialog.Acknowledge, text=TTLocalizer.DistributedPhoneEmpty, text_wordwrap=15, fadeScreen=1, command=self.__clearDialog)
            self.numHouseItems = None
            self.phoneInUse = 0
        elif mode == PhoneGlobals.PHONE_MOVIE_NO_HOUSE:
            if isLocalToon:
                self.phoneDialog = TTDialog.TTDialog(dialogName='PhoneNoHouse', style=TTDialog.Acknowledge, text=TTLocalizer.DistributedPhoneNoHouse, text_wordwrap=15, fadeScreen=1, command=self.__clearDialog)
            self.numHouseItems = None
            self.phoneInUse = 0
        elif mode == PhoneGlobals.PHONE_MOVIE_PICKUP:
            if avatar:
                interval = self.takePhoneInterval(avatar)
                if isLocalToon:
                    self.setupCamera(mode)
                    interval.setDoneEvent(self.pickupMovieDoneEvent)
                    self.acceptOnce(self.pickupMovieDoneEvent, self.__showPhoneGui)
                self.playInterval(interval, elapsed, avatar)
                self.phoneInUse = 1
        elif mode == PhoneGlobals.PHONE_MOVIE_HANGUP:
            if avatar:
                interval = self.replacePhoneInterval(avatar)
                self.playInterval(interval, elapsed, avatar)
            self.numHouseItems = None
            self.phoneInUse = 0
        else:
            self.notify.warning('unknown mode in setMovie: %s' % mode)

    def __showPhoneGui(self):
        if self.toonScale:
            self.sendUpdate('setNewScale', [self.toonScale[0], self.toonScale[1], self.toonScale[2]])

        self.phoneGui = CatalogGUI(self, doneEvent=self.phoneGuiDoneEvent)
        # Hide the phone until we get our popular items set.
        self.phoneGui.hide()
        self.__generateCatalogPages()

        self.acceptOnce('PopularItemsSet', self.__setPopularItems)
        self.cr.catalogManager.fetchPopularItems()

        self.accept(self.phoneGuiDoneEvent, self.__handlePhoneDone)
        self.accept('phoneAsleep', self.__handlePhoneAsleep)

    def __generateCatalogPages(self):
        itemList = base.localAvatar.monthlyCatalog.generateList()
        itemList += base.localAvatar.weeklyCatalog.generateList()
        itemList += base.localAvatar.backCatalog.generateList()

        sortedItems = CatalogItemSorter(itemList).sortItems()

        catalogItemList = CatalogItemListGUI(self.phoneGui)
        for item in sortedItems['FURNITURE']:
            catalogItemList.addItem(item, 'Furniture')
        for item in sortedItems['UNSORTED']:
            catalogItemList.addItem(item, 'Unsorted Items')
        self.phoneGui.tabButtons['FURNITURE_TAB'].setCatalogItemPages(catalogItemList.generatePages())
        self.phoneGui.tabButtons['FURNITURE_TAB'].tabClicked()

        catalogItemList = CatalogItemListGUI(self.phoneGui)
        for item in sortedItems['EMOTIONS']:
            catalogItemList.addItem(item, 'Emotions')
        self.phoneGui.tabButtons['EMOTE_TAB'].setCatalogItemPages(catalogItemList.generatePages())
        self.phoneGui.tabButtons['EMOTE_TAB'].tabClicked()

        catalogItemList = CatalogItemListGUI(self.phoneGui)
        for item in sortedItems['SPECIAL']:
            catalogItemList.addItem(item, 'Special')
        self.phoneGui.tabButtons['SPECIAL_TAB'].setCatalogItemPages(catalogItemList.generatePages())
        self.phoneGui.tabButtons['SPECIAL_TAB'].tabClicked()

        catalogItemList = CatalogItemListGUI(self.phoneGui)
        for item in sortedItems['CLOTHING']:
            catalogItemList.addItem(item, 'Clothing')
        self.phoneGui.tabButtons['CLOTHING_TAB'].setCatalogItemPages(catalogItemList.generatePages())
        self.phoneGui.tabButtons['CLOTHING_TAB'].tabClicked()

        catalogItemList = CatalogItemListGUI(self.phoneGui)
        for item in sortedItems['PHRASES']:
            catalogItemList.addItem(item, 'Phrases')
        self.phoneGui.tabButtons['PHRASES_TAB'].setCatalogItemPages(catalogItemList.generatePages())
        self.phoneGui.tabButtons['PHRASES_TAB'].tabClicked()

        catalogItemList = CatalogItemListGUI(self.phoneGui)
        for item in sortedItems['NAMETAG']:
            catalogItemList.addItem(item, 'Nametag')
        self.phoneGui.tabButtons['NAMETAG_TAB'].setCatalogItemPages(catalogItemList.generatePages())
        self.phoneGui.tabButtons['NAMETAG_TAB'].tabClicked()

    def __setPopularItems(self):
        # Generate a list of popular items.
        itemList = self.cr.catalogManager.popularItems.generateList()
        catalogItemList = CatalogItemListGUI(self.phoneGui)
        for item in itemList:
            catalogItemList.addItem(item, 'Popular')
        self.phoneGui.tabButtons['POPULAR_TAB'].setCatalogItemPages(catalogItemList.generatePages())
        # Now that the popular items are set we can show the CatalogGUI
        self.phoneGui.show()
        # We want our default tab to be the popular tab. We need to click it twice to prevent a glitch.
        self.phoneGui.tabButtons['POPULAR_TAB'].tabClicked()

    def __handlePhoneAsleep(self):
        self.ignore('phoneAsleep')
        if self.phoneGui:
            self.phoneGui.unload()
        self.__handlePhoneDone()

    def requestPurchase(self, item, callback, optional = -1):
        blob = item.getBlob(store=CatalogItem.Customization)
        context = self.getCallbackContext(callback, [item])
        self.sendUpdate('requestPurchaseMessage', [context, blob, optional])

    def requestGiftPurchase(self, item, targetDoID, callback, optional = -1):
        blob = item.getBlob(store=CatalogItem.Customization)
        context = self.getCallbackContext(callback, [item])
        self.sendUpdate('requestGiftPurchaseMessage', [context, targetDoID,
                                                       blob, optional])

    def requestPurchaseResponse(self, context, retcode):
        self.doCallbackContext(context, [retcode])

    def requestGiftPurchaseResponse(self, context, retcode):
        self.doCallbackContext(context, [retcode])

    def __clearDialog(self, event):
        self.phoneDialog.cleanup()
        self.phoneDialog = None
        self.freeAvatar()

    def takePhoneInterval(self, toon):
        torso = TextEncoder.upper(toon.style.torso[0])
        legs = TextEncoder.upper(toon.style.legs[0])
        phoneOutAnim = '%s%s_phoneOut' % (torso, legs)
        takePhoneAnim = '%s%s_takePhone' % (torso, legs)
        phoneNeutralAnim = '%s%s_phoneNeutral' % (torso, legs)
        self.toonScale = toon.getGeomNode().getChild(0).getScale(self.getParent())
        walkTime = 1.0
        scaleTime = 1.0
        origScale = self.getScale()
        origToonPos = toon.getPos()
        origToonHpr = toon.getHpr()
        self.origToonHpr = origToonHpr
        self.setScale(self.toonScale)
        toon.setPosHpr(self, 0, -4.5, 0, 0, 0, 0)
        destToonPos = toon.getPos()
        destToonHpr = toon.getHpr()
        destToonHpr = VBase3(PythonUtil.fitSrcAngle2Dest(destToonHpr[0], origToonHpr[0]), destToonHpr[1], destToonHpr[2])
        self.setScale(origScale)
        toon.setPos(origToonPos)
        toon.setHpr(origToonHpr)
        walkToPhone = Sequence(Func(toon.stopSmooth), Func(toon.loop, 'walk'), Func(base.playSfx, base.localAvatar.soundWalk), toon.posHprInterval(walkTime, destToonPos, destToonHpr, blendType='easeInOut'), Func(toon.loop, 'neutral'), Func(toon.startSmooth))
        interval = Sequence(Parallel(walkToPhone, ActorInterval(self.model, phoneOutAnim), self.scaleInterval(scaleTime, self.toonScale, blendType='easeInOut')), Parallel(ActorInterval(self.model, takePhoneAnim), ActorInterval(toon, 'takePhone'), Sequence(Wait(0.625), Func(base.playSfx, self.pickUpSfx), Func(self.__receiverToHand, toon), Wait(1), Func(base.playSfx, self.handleSfx))), Func(self.model.loop, phoneNeutralAnim), Func(toon.loop, 'phoneNeutral'), Func(base.playSfx, self.ringSfx))
        return interval

    def replacePhoneInterval(self, toon):
        torso = TextEncoder.upper(toon.style.torso[0])
        legs = TextEncoder.upper(toon.style.legs[0])
        phoneBackAnim = '%s%s_phoneBack' % (torso, legs)
        scaleTime = 1.0
        interval = Sequence(Parallel(ActorInterval(self.model, phoneBackAnim), ActorInterval(toon, 'phoneBack'), Sequence(Wait(1.0), Func(self.__receiverToPhone), Func(base.playSfx, self.hangUpSfx))), self.scaleInterval(scaleTime, localAvatar.getGeomNode().getScale()[2], blendType='easeInOut'), Func(toon.loop, 'neutral'))
        if self.origToonHpr:
            interval.append(Func(toon.setHpr, self.origToonHpr))
            self.origToonHpr = None
        if toon == base.localAvatar:
            interval.append(Func(self.freeAvatar))
        return interval

    def __receiverToHand(self, toon):
        self.receiverGeom.reparentTo(toon.leftHand)
        self.receiverGeom.setPosHpr(0.0906813, 0.380375, 0.1, 32.41, 70.68, 137.04)

    def __receiverToPhone(self):
        self.receiverGeom.reparentTo(self.receiverJoint)
        self.receiverGeom.setPosHpr(0, 0, 0, 0, 0, 0)

    def playInterval(self, interval, elapsed, avatar):
        if self.interval != None:
            self.interval.finish()
            self.interval = None
        self.interval = interval
        self.interval.start(elapsed)
        if self.intervalAvatar != avatar:
            if self.intervalAvatar:
                self.ignore(self.intervalAvatar.uniqueName('disable'))
            if avatar:
                self.accept(avatar.uniqueName('disable'), self.clearInterval)
            self.intervalAvatar = avatar

    def clearInterval(self):
        if self.interval != None:
            self.interval.finish()
            self.interval = None
        if self.intervalAvatar:
            self.ignore(self.intervalAvatar.uniqueName('disable'))
            self.intervalAvatar = None
        self.__receiverToPhone()
        self.model.pose('SS_phoneOut', 0)
        self.phoneInUse = 0

    def ringIfHasPhoneQuest(self, task):
        if Quests.avatarHasPhoneQuest(base.localAvatar) and not Quests.avatarHasCompletedPhoneQuest(base.localAvatar):
            self.ring()
        return Task.done

    def ring(self):
        if self.phoneInUse:
            return 0
        phone = self.find('**/prop_phone')
        r = 2.0
        w = 0.05
        shakeOnce = Sequence(Func(phone.setR, r), Wait(w), Func(phone.setR, -r), Wait(w))
        shakeSeq = Sequence()
        for i in xrange(16):
            shakeSeq.append(shakeOnce)

        ringIval = Parallel(Func(base.playSfx, self.ringSfx), shakeSeq, Func(phone.setR, 0))
        self.playInterval(ringIval, 0.0, None)

    def purchaseItemComplete(self):
        self.phoneGui.updateItems()
