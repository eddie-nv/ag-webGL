"""Event name constants for scene mutation events.

Schemas for each payload live in shared/schema/sceneSchema.py.
TypeScript mirror: frontend/lib/agui/customEventTypes.ts +
shared/schema/sceneSchema.ts.
"""

SCENE_OBJECT_ADD = "scene:object_add"
# required: uuid, label, geometryType, geometryArgs[], material{type,color},
#           position[x,y,z], stage
# optional: rotation[x,y,z], scale[x,y,z], visible

SCENE_OBJECT_UPDATE = "scene:object_update"
# required: uuid
# optional: position, rotation, scale, material

SCENE_OBJECT_REMOVE = "scene:object_remove"
# required: uuid

SCENE_CAMERA_MOVE = "scene:camera_move"
# required: position[x,y,z], target[x,y,z]
# optional: fov

SCENE_LIGHT_ADD = "scene:light_add"
# required: uuid, lightType (DirectionalLight|AmbientLight|PointLight),
#           color, intensity
# optional: position[x,y,z]

SCENE_ANIMATION_START = "scene:animation_start"
# required: uuid, animationType, duration
# optional: axis, from, to, loop, easing

SCENE_ANIMATION_STOP = "scene:animation_stop"
# required: uuid

SCENE_CONTROL_PANEL = "scene:control_panel"
# required: id, controls
# optional: title
# Inline UI rendered as a chat bubble. Each control has a `kind` discriminator:
# 'button' (one-shot, fires `emits` events) or 'toggle' (stateful on/off).
