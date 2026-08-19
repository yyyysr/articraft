# Physics Parameters

## Responsibility Boundary

Use this page when mass distribution, contact behavior, or passive joint
behavior matters to simulation. Author physics in `model.py`; there is no
separate physics-plan file.

- The author selects plausible part masses, material classes, and meaningful
  joint behavior from object semantics.
- The SDK validates values, derives unresolved mass properties, and exports the
  representation supported by each format.
- Generic defaults are compatibility fallbacks, not successful inference.

Use explicit authored values first, documented semantic priors second, generic
fallbacks third, and emergency collision-based estimation last.

## Physical Materials

```python
PhysicsMaterial(
    name: str,
    density: float,
    static_friction: float,
    dynamic_friction: float,
    restitution: float,
)
```

Create a reusable material for each distinct bulk/contact class and assign it
to relevant parts. Keep dynamic friction no greater than static friction.

Broad density priors in `kg/m^3`:

| Material class | Density |
| --- | ---: |
| wood and engineered wood | 400-850 |
| common rigid plastic | 900-1400 |
| rubber and elastomer | 900-1300 |
| glass | 2200-2600 |
| aluminum alloy | 2600-2900 |
| steel and stainless steel | 7600-8050 |

Broad contact priors:

| Surface class | Static friction | Dynamic friction | Restitution |
| --- | ---: | ---: | ---: |
| smooth plastic or paint | 0.3-0.6 | 0.2-0.5 | 0.02-0.2 |
| dry wood | 0.4-0.7 | 0.3-0.6 | 0.05-0.3 |
| dry metal | 0.3-0.7 | 0.2-0.5 | 0.02-0.3 |
| glass | 0.3-0.6 | 0.2-0.5 | 0.05-0.4 |
| rubber grip or tire | 0.7-1.2 | 0.6-1.0 | 0.1-0.8 |

These ranges are starting priors. Surface finish, contamination, contact
partner, and solver rules can dominate observed behavior.

## Mass And Inertia

Prefer a plausible assembled-part mass over a solid-volume estimate for hollow
or composite construction. Appliances, furniture, enclosures, doors, and
drawers are rarely solid volumes of their visible bulk material.

Use `Inertial.from_geometry(...)` for a primitive when its mass is known. Let
the SDK derive unresolved mass properties only when collision geometry is a
reasonable proxy for mass distribution. Do not invent a detailed inertia tensor
for a complex mesh without evidence.

Fill factors can sanity-check a mass estimate but must not be encoded as
collision scale:

| Construction | Bounding-box fill factor |
| --- | ---: |
| solid casting or block | 0.7-0.9 |
| dense machined assembly | 0.3-0.5 |
| thin panel or shell | 0.05-0.15 |
| hollow tube or frame | 0.01-0.05 |
| sheet-metal enclosure | 0.005-0.02 |

## Passive Joint Dynamics

```python
MotionProperties(
    damping: float | None = None,
    friction: float | None = None,
    stiffness: float | None = None,
    equilibrium: float | None = None,
)
```

For revolute/continuous joints, damping is `N*m*s/rad`, friction is `N*m`,
stiffness is `N*m/rad`, and equilibrium is radians. For prismatic joints,
damping is `N*s/m`, friction is `N`, stiffness is `N/m`, and equilibrium is
meters.

Apply these conditionally:

- Damping limits motion speed but does not statically hold a gravity-loaded
  mechanism.
- Friction represents passive resistance, not a positional target.
- Stiffness and equilibrium create a restoring/preload behavior and should be
  used only when that behavior exists.
- Explicit zero damping/friction represents an intentionally free joint.
- Omitted motion properties mean unresolved dynamics and produce a warning on
  movable joints.

### Gravity-sensitive folding joints

Use the following approximation only when the closed pose tends to open under
gravity and should require external force:

1. Estimate `tau_g = mass * 9.81 * horizontal_lever_arm`.
2. Put `equilibrium` at the closed-side target and choose preload around
   `1.1-1.3 * tau_g` through `stiffness`.
3. Set `MotionLimits.effort`, exported as USD drive `maxForce`, near the needed
   preload rather than far above it. This limits large-angle return force.
4. Add only enough damping to control speed.

A fixed target drive still creates some return torque after opening. A true
breakaway latch or detent that releases after opening requires runtime state and
must not be implied for unrelated assets.

## Fallbacks And Diagnostics

- `physics_material=None`: use generic material fallback and warn.
- `motion_properties=None`: leave movable-joint dynamics unresolved and warn.
- Explicit zero damping/friction: intentionally free joint; do not warn.
- `inertial=None`: derive mass properties from collision geometry and density;
  USD records `articraft:inertialSource="estimated_collision"`.

Warnings are non-blocking for backward compatibility. Resolve them when object
semantics provide evidence; do not silence them with invented precision.

## Export Matrix

| Parameter | OpenUSD | URDF |
| --- | --- | --- |
| mass, center of mass, inertia | `PhysicsMassAPI` | `<inertial>` |
| density | `PhysicsMaterialAPI` | resolved into mass properties |
| friction and restitution | `PhysicsMaterialAPI` | no core representation |
| joint axis and bounds | physics joint schemas | `<axis>`, `<limit>` |
| damping | `PhysicsDriveAPI` | `<dynamics damping>` |
| joint friction | `articraft:jointFriction` | `<dynamics friction>` |

Stiffness/equilibrium are portable in standard OpenUSD `PhysicsDriveAPI` but
have no core URDF equivalent. `MotionLimits.effort` becomes USD drive
`maxForce` and URDF joint limit `effort`; it is not a friction model. Do not add
PhysX-specific schema fields to portable authoring.
