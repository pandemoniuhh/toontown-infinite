from direct.actor.DistributedActor import DistributedActor
from direct.distributed import DistributedNode
from direct.interval.IntervalGlobal import *
from toontown.util import PythonUtil
from direct.task import Task
from panda3d.core import *

from Avatar import Avatar
from otp.ai.MagicWordGlobal import *
from otp.otpbase import OTPGlobals
from toontown.battle.BattleProps import globalPropPool


class DistributedAvatar(DistributedActor, Avatar):
    HpTextGenerator = TextNode('HpTextGenerator')
    HpTextEnabled = 1
    ManagesNametagAmbientLightChanged = True

    def __init__(self, cr):
        try:
            self.DistributedAvatar_initialized
            return
        except:
            self.DistributedAvatar_initialized = 1

        Avatar.__init__(self)
        DistributedActor.__init__(self, cr)
        self.hpText = None
        self.hp = None
        self.maxHp = None
        return

    def disable(self):
        try:
            del self.DistributedAvatar_announced
        except:
            return

        self.reparentTo(hidden)
        self.removeActive()
        self.disableBodyCollisions()
        self.hideHpText()
        self.hp = None
        self.ignore('nameTagShowAvId')
        self.ignore('nameTagShowName')
        DistributedActor.disable(self)
        return

    def delete(self):
        try:
            self.DistributedAvatar_deleted
        except:
            self.DistributedAvatar_deleted = 1
            Avatar.delete(self)
            DistributedActor.delete(self)

    def generate(self):
        DistributedActor.generate(self)
        if not self.isLocal():
            self.addActive()
            self.considerUnderstandable()
        self.setParent(OTPGlobals.SPHidden)
        self.setTag('avatarDoId', str(self.doId))
        self.accept('nameTagShowAvId', self.__nameTagShowAvId)
        self.accept('nameTagShowName', self.__nameTagShowName)

    def announceGenerate(self):
        try:
            self.DistributedAvatar_announced
            return
        except:
            self.DistributedAvatar_announced = 1

        if not self.isLocal():
            self.initializeBodyCollisions('distAvatarCollNode-' + str(self.doId))
        DistributedActor.announceGenerate(self)

    def __setTags(self, extra = None):
        if hasattr(base, 'idTags'):
            if base.idTags:
                self.__nameTagShowAvId()
            else:
                self.__nameTagShowName()

    def do_setParent(self, parentToken):
        if not self.isDisabled():
            nametag2d = self.nametag.getNametag2d()
            if parentToken == OTPGlobals.SPHidden:
                nametag2d.hideNametag()
            else:
                nametag2d.showNametag()
            nametag2d.update()
            DistributedActor.do_setParent(self, parentToken)
            self.__setTags()

    def toonUp(self, hpGained):
        if self.hp == None or hpGained < 0:
            return
        oldHp = self.hp
        if self.hp + hpGained <= 0:
            self.hp += hpGained
        else:
            self.hp = min(max(self.hp, 0) + hpGained, self.maxHp)
        hpGained = self.hp - max(oldHp, 0)
        if hpGained > 0:
            self.showHpText(hpGained)
            self.hpChange(quietly=0)
        return

    def takeDamage(self, hpLost, bonus = 0):
        if self.hp == None or hpLost < 0:
            return
        oldHp = self.hp
        self.hp = max(self.hp - hpLost, 0)
        hpLost = oldHp - self.hp
        if hpLost > 0:
            self.showHpText(-hpLost, bonus)
            self.hpChange(quietly=0)
            if self.hp <= 0 and oldHp > 0:
                self.died()
        return

    def setHp(self, hitPoints):
        justRanOutOfHp = (hitPoints is not None and self.hp is not None and self.hp - hitPoints > 0) and (hitPoints <= 0)
        self.hp = hitPoints
        self.hpChange(quietly=1)
        if justRanOutOfHp:
            self.died()
        return

    def hpChange(self, quietly = 0):
        if hasattr(self, 'doId'):
            if self.hp != None and self.maxHp != None:
                messenger.send(self.uniqueName('hpChange'), [self.hp, self.maxHp, quietly])
            if self.hp != None and self.hp > 0:
                messenger.send(self.uniqueName('positiveHP'))
        return

    def died(self):
        pass

    def getHp(self):
        return self.hp

    def setMaxHp(self, hitPoints):
        self.maxHp = hitPoints
        self.hpChange()

    def getMaxHp(self):
        return self.maxHp

    def getName(self):
        return Avatar.getName(self)

    def setName(self, name):
        try:
            self.node().setName('%s-%d' % (name, self.doId))
            self.gotName = 1
        except:
            pass

        return Avatar.setName(self, name)

    def showHpText(self, number, bonus = 0, scale = 1):
        if self.HpTextEnabled and not self.ghostMode:
            if number != 0:
                if self.hpText:
                    self.hideHpText()
                self.HpTextGenerator.setFont(OTPGlobals.getSignFont())
                if number < 0:
                    self.HpTextGenerator.setText(str(number))
                else:
                    self.HpTextGenerator.setText('+' + str(number))
                self.HpTextGenerator.clearShadow()
                self.HpTextGenerator.setAlign(TextNode.ACenter)
                if bonus == 1:
                    r = 1.0
                    g = 1.0
                    b = 0
                    a = 1
                elif bonus == 2:
                    r = 1.0
                    g = 0.5
                    b = 0
                    a = 1
                elif number < 0:
                    r = 0.9
                    g = 0
                    b = 0
                    a = 1
                else:
                    r = 0
                    g = 0.9
                    b = 0
                    a = 1
                self.HpTextGenerator.setTextColor(r, g, b, a)
                self.hpTextNode = self.HpTextGenerator.generate()
                self.hpText = self.attachNewNode(self.hpTextNode)
                self.hpText.setScale(scale)
                self.hpText.setBillboardPointEye()
                self.hpText.setBin('fixed', 100)
                self.hpText.setPos(0, 0, self.height / 2)
                seq = Sequence(self.hpText.posInterval(1.0, Point3(0, 0, self.height + 1.5), blendType='easeOut'), Wait(0.85), self.hpText.colorInterval(0.1, Vec4(r, g, b, 0)), Func(self.hideHpText))
                seq.start()

    def showHpString(self, text, duration = 0.85, scale = 0.7):
        if self.HpTextEnabled and not self.ghostMode:
            if text != '':
                if self.hpText:
                    self.hideHpText()
                self.HpTextGenerator.setFont(OTPGlobals.getSignFont())
                self.HpTextGenerator.setText(text)
                self.HpTextGenerator.clearShadow()
                self.HpTextGenerator.setAlign(TextNode.ACenter)
                r = a = 1.0
                g = b = 0.0
                self.HpTextGenerator.setTextColor(r, g, b, a)
                self.hpTextNode = self.HpTextGenerator.generate()
                self.hpText = self.attachNewNode(self.hpTextNode)
                self.hpText.setScale(scale)
                self.hpText.setBillboardAxis()
                self.hpText.setPos(0, 0, self.height / 2)
                seq = Sequence(self.hpText.posInterval(1.0, Point3(0, 0, self.height + 1.5), blendType='easeOut'), Wait(duration), self.hpText.colorInterval(0.1, Vec4(r, g, b, 0)), Func(self.hideHpText))
                seq.start()

    def hideHpText(self):
        if self.hpText:
            taskMgr.remove(self.uniqueName('hpText'))
            self.hpText.removeNode()
            self.hpText = None
        return

    def getStareAtNodeAndOffset(self):
        return (self, Point3(0, 0, self.height))

    def getAvIdName(self):
        return '%s\n%s' % (self.getName(), self.doId)

    def __nameTagShowAvId(self, extra = None):
        self.setDisplayName(self.getAvIdName())

    def __nameTagShowName(self, extra = None):
        self.setDisplayName(self.getName())

    def askAvOnShard(self, avId):
        if base.cr.doId2do.get(avId):
            messenger.send('AvOnShard%s' % avId, [True])
        else:
            self.sendUpdate('checkAvOnShard', [avId])

    def confirmAvOnShard(self, avId, onShard = True):
        messenger.send('AvOnShard%s' % avId, [onShard])

    def getDialogueArray(self):
        return None


@magicWord(category=CATEGORY_COMMUNITY_MANAGER)
def warp():
    """
    warp the target to the invoker's current position, and rotation.
    """
    invoker = spellbook.getInvoker()
    target = spellbook.getTarget()
    if invoker.doId == target.doId:
        return "You can't warp yourself!"
    target.setPosHpr(invoker.getPos(), invoker.getHpr())


@magicWord(category=CATEGORY_COMMUNITY_MANAGER, types=[str])
def loop(anim):
    """
    animate the target using animation [anim] on the entire actor.
    """
    target = spellbook.getTarget()
    target.loop(anim)


@magicWord(category=CATEGORY_COMMUNITY_MANAGER, types=[str, int, str])
def pose(anim, frame, part=None):
    """
    freeze the target on frame [frame] of animation [anim] on the entire actor,
    or optional [part] of the actor.
    """
    target = spellbook.getTarget()
    target.pose(anim, frame, partName=part)


@magicWord(category=CATEGORY_COMMUNITY_MANAGER, types=[str, int, int, str])
def pingpong(anim, start=None, end=None, part=None):
    """
    animate the target by bouncing back and forth between the start and end, or
    the optional frames <start>, and [end] of animation [anim] on the entire
    actor, or optional <part> of the actor.
    """
    target = spellbook.getTarget()
    target.pingpong(anim, partName=part, fromFrame=start, toFrame=end)

@magicWord(category=CATEGORY_COMMUNITY_MANAGER, types=[str])
def rightHand(prop=None):
    """
    parents the optional <prop> to the target's right hand node.
    """
    target = spellbook.getTarget()
    rightHand = target.find('**/rightHand')
    if prop is None:
        for child in rightHand.getChildren():
            child.removeNode()
    else:
        for child in rightHand.getChildren():
            child.removeNode()
        requestedProp = globalPropPool.getProp(prop)
        requestedProp.reparentTo(rightHand)

@magicWord(category=CATEGORY_COMMUNITY_MANAGER, types=[str])
def leftHand(prop=None):
    """
    parents the optional <prop> to the target's left hand node.
    """
    target = spellbook.getTarget()
    leftHand = target.find('**/leftHand')
    if prop is None:
        for child in leftHand.getChildren():
            child.removeNode()
    else:
        for child in leftHand.getChildren():
            child.removeNode()
        requestedProp = globalPropPool.getProp(prop)
        requestedProp.reparentTo(leftHand)
