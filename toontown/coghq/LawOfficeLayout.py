import random

from direct.directnotify import DirectNotifyGlobal
from toontown.util.PythonUtil import invertDictLossless
from toontown.util.PythonUtil import normalDistrib, lerp
from toontown.coghq import MintRoomSpecs
from toontown.toonbase import ToontownGlobals


OfficeBuildingFloorSequences = {
    13300: [
        (0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0)] }
Index2Spec = {
    0: 'LawOffice_Spec_Tier0_a',
    1: 'LawOffice_Spec_Tier0_b' }
LawbotFloorSpecs = {}
for floorIndex, floorSpec in Index2Spec.items():
    LawbotFloorSpecs[floorIndex] = __import__('toontown.coghq.' + floorSpec)


class LawOfficeLayout:
    notify = DirectNotifyGlobal.directNotify.newCategory('MintLayout')

    def __init__(self, lawOfficeId):
        self.lawOfficeId = lawOfficeId
        self.floorIds = []
        if self.lawOfficeId in OfficeBuildingFloorSequences:
            self.floorIds = OfficeBuildingFloorSequences[self.lawOfficeId][random.randint(0, len(OfficeBuildingFloorSequences[self.lawOfficeId])) - 1]
        else:
            self.notify.warning('no layout for Law Office ID: using defaults')
            self.floorIds = (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)


    def getFloorId(self, index):
        return self.floorIds[index]


    def getFloorSpec(self, index):
        return LawbotFloorSpecs[self.floorIds[index]]


    def getFloorIds(self):
        return self.floorIds


