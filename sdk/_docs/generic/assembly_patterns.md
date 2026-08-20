# Common Assembly Patterns

Use these small patterns as starting points for common rigid-part structures.
They are intentionally minimal: establish part frames, parent-child relations,
and motion first, then add product-specific geometry and details.

## Visual Binding

`Part.visual` takes geometry as its positional argument. Pass appearance with
the keyword `material=` (or `color=`), and keep the visual name explicit when
tests or overlap diagnostics need to identify it.

```python
from sdk import Box, Origin

body = model.part("body")
finish = model.material("finish", rgba=(0.2, 0.2, 0.2, 1.0))
body.visual(
    Box((0.6, 0.4, 0.8)),
    material=finish,
    name="body_shell",
)
```

Do not pass origin, material, or color as extra positional arguments.

## Fixed Rigid Attachment

Use a fixed articulation only when the child must be a separate rigid body but
has no relative motion. The enum form avoids invalid string casing.

```python
from sdk import ArticulationType

model.articulation(
    "shelf_mount",
    ArticulationType.FIXED,
    parent="cabinet",
    child="shelf",
    origin=Origin(xyz=(0.0, 0.0, 0.8)),
)
```

## Bounded Revolute Door

The child door is authored in its own frame. Put the hinge origin at the door
pivot, and use explicit angular limits in radians.

```python
from sdk import ArticulationType, MotionLimits, MotionProperties

model.articulation(
    "door_hinge",
    ArticulationType.REVOLUTE,
    parent="cabinet",
    child="door",
    origin=Origin(xyz=(0.30, 0.0, 0.45)),
    axis=(0.0, 0.0, 1.0),
    motion_limits=MotionLimits(
        effort=30.0,
        velocity=1.5,
        lower=0.0,
        upper=2.1,
    ),
    motion_properties=MotionProperties(damping=0.25, friction=0.05),
)
```

`REVOLUTE` and `PRISMATIC` require both `lower` and `upper`. If the joint is
intentionally unbounded, use `CONTINUOUS` and omit position bounds.

## Bounded Prismatic Drawer

Place the drawer geometry in the child frame at the closed position. The axis
direction defines the positive opening direction.

```python
model.articulation(
    "drawer_slide",
    ArticulationType.PRISMATIC,
    parent="cabinet",
    child="drawer",
    origin=Origin(xyz=(0.0, 0.0, 0.35)),
    axis=(0.0, 1.0, 0.0),
    motion_limits=MotionLimits(
        effort=120.0,
        velocity=0.5,
        lower=0.0,
        upper=0.45,
    ),
    motion_properties=MotionProperties(damping=1.0, friction=0.2),
)
```

Keep a retained portion of the slide or drawer body inside the cabinet at
maximum travel; do not position the child as a floating object at zero pose.

## Continuous Swivel Seat

Use `CONTINUOUS` for an unbounded swivel. It requires effort and velocity but
must not receive `lower` or `upper` limits.

```python
model.articulation(
    "seat_swivel",
    ArticulationType.CONTINUOUS,
    parent="base",
    child="seat",
    origin=Origin(xyz=(0.0, 0.0, 0.7)),
    axis=(0.0, 0.0, 1.0),
    motion_limits=MotionLimits(effort=20.0, velocity=4.0),
    motion_properties=MotionProperties(damping=0.15, friction=0.05),
)
```

## Connection Checklist

- Every moving part has exactly one incoming articulation.
- The child frame is authored at the joint's zero pose.
- Parent and child have intentional contact or retained insertion at zero pose.
- Joint axis and positive direction match the intended opening or sliding motion.
- Add overlap allowances only for named, intentional embedded features, with an
  exact proof check; do not use allowances to hide misplaced parts.

## Exterior Finish Checklist

Before duplicating a panel, door, drawer, or seat construction, replace the
sharp placeholder volume when the real object has a visible transition:

- use a rounded profile or CadQuery fillet for exposed appliance and furniture
  edges;
- use a dome, capsule, or loft for padded seating instead of stacked cylinders;
- use a lathed or tapered section for a pedestal or weighted base;
- use a sweep or torus for tubular rails and footrests.

Keep hidden fasteners and internal supports primitive unless their geometry
affects contact, clearance, or the visible silhouette.

For exposed hinge leaves, knuckles, and pin geometry, read
`docs/sdk/references/components/hinges.md`. For mass, contact, and passive joint
dynamics, read `docs/sdk/references/physics-parameters.md`.
