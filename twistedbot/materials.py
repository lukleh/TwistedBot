

class Material(object):
    is_solid = True
    is_liquid = False
    blocks_movement = True
    is_translucent = False

    def __init__(self, translucent=None):
        if translucent is not None:
            self.is_translucent = translucent

    @property
    def is_opaque(self):
        if self.is_translucent:
            return False
        else:
            return self.blocks_movement


class MaterialTransparent(Material):
    is_solid = False
    blocks_movement = False


class MaterialLiquid(Material):
    is_solid = False
    is_liquid = True
    blocks_movement = False


class MaterialLogic(Material):
    is_solid = False
    blocks_movement = False


class MaterialPortal(Material):
    is_solid = False
    blocks_movement = False


class MaterialPortal(Material):
    blocks_movement = False


class MaterialWeb(Material):
    blocks_movement = False


air = MaterialTransparent()
grass = Material()
ground = Material()
wood = Material()
rock = Material()
iron = Material()
water = MaterialLiquid()
lava = MaterialLiquid()
leaves = Material(translucent=True)
plants = Material()
vine = Material()
sponge = Material()
cloth = Material()
fire = MaterialTransparent()
sand = Material()
circuits = MaterialLogic()
glass = Material(translucent=True)
redstone_light = Material()
tnt = Material(translucent=True)
ice = Material(translucent=True)
snow = Material(translucent=True)
crafted_snow = Material()
cactus = Material(translucent=True)
clay = Material()
pumpkin = Material()
dragon_egg = Material()
portal = MaterialPortal()
cake = Material()
web = MaterialWeb()
piston = Material()
