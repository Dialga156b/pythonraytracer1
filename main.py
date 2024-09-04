import pygame
import math
import colorsys
import time

pygame.init()
screenWidth = 300
screenHeight = int(screenWidth * (9/16))
screen = pygame.display.set_mode((screenWidth, screenHeight))
clock = pygame.time.Clock()
running = True
screen.fill('black')

fov = math.radians(90)  # FOV in radians
maxDist = 75
maxReflectionDist = 50
renderQuality = .5  # Percentage (impacts render speed)
showLightSourceReflection = True # that little dot that looks like the sun on certain objects

def calculate_ray_steps(pixelX, pixelY, screenWidth, screenHeight, fov):
    rayX = screenWidth // 2
    rayY = screenHeight // 2

    aspect_ratio = screenWidth / screenHeight
    fov_adjustment = math.tan(fov / 2)

    xStep = (pixelX - rayX) / screenWidth * 2 * aspect_ratio * fov_adjustment
    yStep = (pixelY - rayY) / screenHeight * 2 * fov_adjustment
    zStep = 1

    magnitude = math.sqrt(xStep**2 + yStep**2 + zStep**2) * (renderQuality*5)
    xStep /= magnitude
    yStep /= magnitude
    zStep /= magnitude

    return xStep, yStep, zStep

objectTable = [
    [
        {"Name": "Sphere_SnowmanBase", "Position": (-5, 10, 30), "Size": (25, 25, 25), "Color": (255, 255, 255),"Reflective":True},
        {"Name": "Sphere_SnowmanMiddle", "Position": (-5, 0, 30), "Size": (20, 20, 20), "Color": (255, 255, 255),"Reflective":True},
        {"Name": "Sphere_SnowmanHead", "Position": (-5, -10, 30), "Size": (15, 15, 15), "Color": (255, 255, 255),"Reflective":True},
        {"Name": "Sphere_SnowmanEye", "Position": (-6, -8, 20), "Size": (1.5, 1.5, 1.5), "Color": (30, 30, 30),"Reflective":False},
        {"Name": "Sphere_SnowmanEye", "Position": (-2, -8, 20), "Size": (1.5, 1.5, 1.5), "Color": (30, 30, 30),"Reflective":False},
        {"Name": "Cube", "Position": (25, 5, 40), "Size": (25, 25, 25), "Color": (3, 111, 252),"Reflective":False},
        {"Name": "Cube2", "Position": (-19, 15, 19), "Size": (8.5,8.5,5.5), "Color": (198, 52, 235),"Reflective":False},
        {"Name": "SphereMisc3", "Position": (-19, 6, 19), "Size": (6,6,6), "Color": (235, 222, 89),"Reflective":True},
        {"Name": "Cube_Floor", "Position": (0, 18, 50), "Size": (100, 1, 100), "Color": (85, 103, 200),"Reflective":False},
    ]
]

lightTable = [
    [
        {"Name": "LightSource_1", "Position": (33, -25, 0)},
    ]
]

def checkCollisions(pos_x, pos_y, pos_z):
    for obj_list in objectTable:
        for obj in obj_list:
            name = obj["Name"]
            position = obj["Position"]
            if "Cube" in name:
                size = obj["Size"]
                color = obj["Color"]
                if (position[0] - size[0] / 2 <= pos_x <= position[0] + size[0] / 2 and
                    position[1] - size[1] / 2 <= pos_y <= position[1] + size[1] / 2 and
                    position[2] - size[2] / 2 <= pos_z <= position[2] + size[2] / 2):
                    return True, color, obj
            if "Sphere" in name:
                size = obj["Size"]
                color = obj["Color"]
                distance = math.sqrt(
                    (pos_x - position[0])**2 +
                    (pos_y - position[1])**2 +
                    (pos_z - position[2])**2
                )
                if distance <= size[0] / 2:
                    return True, color, obj
    return False, None, None

def checkShadowed(x, y, z):
    unshadowed_by_any = True
    for obj in lightTable:
        for LightSource in obj:
            LPosX = LightSource["Position"][0]
            LPosY = LightSource["Position"][1]
            LPosZ = LightSource["Position"][2]

            dist = math.sqrt(
                (LPosX - x) ** 2 +
                (LPosY - y) ** 2 +
                (LPosZ - z) ** 2
            )
            for m in range(1, int(dist)):
                t = m / dist

                newX = x + t * (LPosX - x)
                newY = y + t * (LPosY - y)
                newZ = z + t * (LPosZ - z)
                isIntersected, _, _  = checkCollisions(newX, newY, newZ)
                if isIntersected:
                    unshadowed_by_any = False
                    break
            if unshadowed_by_any:
                break
    return not unshadowed_by_any

def get_surface_normal(obj, x, y, z):
    # oh my god i have no clue what any of this means
    if "Sphere" in obj["Name"]:
        centerX, centerY, centerZ = obj["Position"]
        normalX = (x - centerX)
        normalY = (y - centerY)
        normalZ = (z - centerZ)
        magnitude = math.sqrt(normalX**2 + normalY**2 + normalZ**2)
        normalX /= magnitude
        normalY /= magnitude
        normalZ /= magnitude
    elif "Cube" in obj["Name"]:
        centerX, centerY, centerZ = obj["Position"]
        sizeX, sizeY, sizeZ = obj["Size"]

        epsilon = 1e-5  #teeny tiny numbah
        if abs(x - (centerX - sizeX/2)) < epsilon:
            normalX, normalY, normalZ = -1, 0, 0  # Left face
        elif abs(x - (centerX + sizeX/2)) < epsilon:
            normalX, normalY, normalZ = 1, 0, 0  # Right face
        elif abs(y - (centerY - sizeY/2)) < epsilon:
            normalX, normalY, normalZ = 0, -1, 0  # Bottom face
        elif abs(y - (centerY + sizeY/2)) < epsilon:
            normalX, normalY, normalZ = 0, 1, 0  # Top face
        elif abs(z - (centerZ - sizeZ/2)) < epsilon:
            normalX, normalY, normalZ = 0, 0, -1  # Back face
        elif abs(z - (centerZ + sizeZ/2)) < epsilon:
            normalX, normalY, normalZ = 0, 0, 1  # Front face
        else:
            normalX, normalY, normalZ = 0, 0, 0  # Default

    return normalX, normalY, normalZ

def getReflections(x, y, z, objName, xStep, yStep, zStep, depth=1, maxDepth=8):
    for obj in objectTable[0]:
        if obj["Name"] == objName:
            NormX, NormY, NormZ = get_surface_normal(obj, x, y, z)

            reflect_xStep = xStep - 2 * (xStep * NormX + yStep * NormY + zStep * NormZ) * NormX
            reflect_yStep = yStep - 2 * (xStep * NormX + yStep * NormY + zStep * NormZ) * NormY
            reflect_zStep = zStep - 2 * (xStep * NormX + yStep * NormY + zStep * NormZ) * NormZ
            if depth > maxDepth:
                BGr, BGg, BGb = colorsys.hsv_to_rgb(.607, .25, .8)
                originalColor = obj["Color"]
                return (
                    (BGr * 255 * 0.7 + originalColor[0] * 0.3),
                    (BGg * 255 * 0.7 + originalColor[1] * 0.3),
                    (BGb * 255 * 0.7 + originalColor[2] * 0.3)
                )
            for i in range(1, maxReflectionDist):
                newX = x + reflect_xStep * i
                newY = y + reflect_yStep * i
                newZ = z + reflect_zStep * i

                isIntersected, hitColor, hitObject = checkCollisions(newX, newY, newZ)

                if isIntersected:
                    if checkShadowed(newX,newY,newZ):
                        hitR = hitColor[0]
                        hitG = hitColor[1]
                        hitB = hitColor[2]
                        hitColor = (hitR*.6,hitG*.6,hitB*.6)
                    if hitObject and hitObject.get("Reflective", False):
                        recursiveColor = getReflections(newX, newY, newZ, hitObject["Name"], reflect_xStep, reflect_yStep, reflect_zStep, depth + 1, maxDepth)
                        if recursiveColor:
                            return recursiveColor
                    return hitColor
            BGr, BGg, BGb = colorsys.hsv_to_rgb(.607, .25, .8)
            originalColor = obj["Color"]
            return (
                (BGr * 255 * 0.7 + originalColor[0] * 0.3),
                (BGg * 255 * 0.7 + originalColor[1] * 0.3),
                (BGb * 255 * 0.7 + originalColor[2] * 0.3)
            )

def renderPixel(pixelX, pixelY, render_Shadows):
    xPos, yPos, zPos = 0, 0, 0
    xStep, yStep, zStep = calculate_ray_steps(pixelX, pixelY, screenWidth, screenHeight, fov)
    timedout = False
    objColor = None
    object = None
    gradientblue = pixelY / screenHeight
    BGr, BGg, BGb = colorsys.hsv_to_rgb(.607, gradientblue * 0.43, .95)
    
    while not timedout:
        collision, objColor, object = checkCollisions(xPos, yPos, zPos)
        if collision:
            break
        xPos += xStep
        yPos += yStep
        zPos += zStep
        dist = math.sqrt(xPos**2 + yPos**2 + zPos**2)
        if dist >= maxDist:
            screen.set_at((pixelX, pixelY), (BGr * 255, BGg * 255, BGb * 255))
            timedout = True
            break
    
    if not timedout:
        value = dist / maxDist
        value = min(max(value, 0), 1)  # precaution
        reflectionColor = None
        if object["Reflective"]:
            objName = object["Name"]
            reflectionColor = getReflections(xPos, yPos, zPos, objName, xStep, yStep, zStep)
            if reflectionColor:
                objColor = reflectionColor
        r, g, b = objColor
        colorCap = 255
        if render_Shadows:
            isShadowed = checkShadowed(xPos, yPos, zPos)
            if isShadowed and reflectionColor is not None:
                colorCap = 100
            elif isShadowed:
                colorCap = 60
        final_r = min(max(int(r * value + BGr * colorCap * value), 0), colorCap)
        final_g = min(max(int(g * value + BGg * colorCap * value), 0), colorCap)
        final_b = min(max(int(b * value + BGb * colorCap * value), 0), colorCap)
        screen.set_at((pixelX, pixelY), (final_r, final_g, final_b))

def renderImg():
    pygame.init()
    render_Shadows = True
    if renderQuality <= .3 :
        render_Shadows = False
    start_time = time.time()
    for pixelY in range(screenHeight):
        elapsed_time = time.time() - start_time
        pygame.display.set_caption(f"Renderer: Rendering | [{(pixelY / screenHeight) * 100:.1f}%] | Time Elapsed: {elapsed_time:.2f} seconds")
        pygame.display.flip()
        for pixelX in range(screenWidth):
            renderPixel(pixelX,pixelY,render_Shadows)
    pygame.display.set_caption(f"Done! [{time.time() - start_time:.2f}s]")
    pygame.display.flip()

renderImg()

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
    pygame.display.flip()
    clock.tick(60)
