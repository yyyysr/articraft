# Physics Parameters

## Purpose

Use this reference when an asset's material, mass distribution, contact
behavior, or passive joint behavior affects its intended simulation. Physics
parameters are authored directly in `model.py`; do not create a separate JSON
physics-plan input.

## Responsibility Boundary

- The agent identifies part roles, material/construction classes, plausible
  masses, and behaviorally important joint dynamics.
- The SDK validates values, derives unresolved mass properties, and exports the
  supported OpenUSD and URDF representations.
- Generic defaults are a safety fallback, not a successful material inference.
- Compile warnings disclose unresolved material and joint-dynamics choices.

Use this precedence order:

1. Explicit `Inertial`, `PhysicsMaterial`, and `MotionProperties` values.
2. A documented material or mechanism prior selected from asset semantics.
3. Generic SDK defaults.
4. Emergency collision-geometry estimation.

## Applicability

These rules are conditional on the asset semantics; do not apply the same
joint settings to every asset. Author nonzero passive dynamics only when a
mechanism has meaningful resistance, such as a damped appliance door, a
gravity-loaded flap, or a drawer with rail friction. Deliberately free joints
should use explicit zero damping/friction, while static or fixed mechanisms do
not need `MotionProperties` at all.

## Physical Material Authoring

Create one reusable `PhysicsMaterial` per distinct bulk/contact class and pass
it to the relevant parts:

```python
painted_steel = PhysicsMaterial(
    name="painted_steel",
    density=7850.0,
    static_friction=0.5,
    dynamic_friction=0.35,
    restitution=0.05,
)

cabinet = model.part("cabinet", physics_material=painted_steel)
door = model.part("door", physics_material=painted_steel)
```

Starting density ranges for bulk materials:

| Class | Density (kg/m^3) |
| --- | ---: |
| wood and engineered wood | 400-850 |
| common rigid plastic | 900-1400 |
| rubber and elastomer | 900-1300 |
| glass | 2200-2600 |
| aluminum alloy | 2600-2900 |
| steel and stainless steel | 7600-8050 |

These are material densities, not assembled-object densities. Appliances,
furniture, enclosures, doors, and drawers are usually hollow or composite. Do
not multiply their complete bounding-box volume by bulk density and treat the
result as a realistic total mass.

Starting contact ranges depend on both contacting surfaces and finish:

| Surface class | Static friction | Dynamic friction | Restitution |
| --- | ---: | ---: | ---: |
| smooth plastic/painted surface | 0.3-0.6 | 0.2-0.5 | 0.02-0.2 |
| dry wood | 0.4-0.7 | 0.3-0.6 | 0.05-0.3 |
| dry metal | 0.3-0.7 | 0.2-0.5 | 0.02-0.3 |
| glass | 0.3-0.6 | 0.2-0.5 | 0.05-0.4 |
| rubber grip/tire | 0.7-1.2 | 0.6-1.0 | 0.1-0.8 |

Treat these as broad priors. Surface coating, contamination, contact partner,
and solver combination rules can dominate the final behavior. Keep dynamic
friction no greater than static friction.

## Mass And Inertia

Prefer a plausible assembled-part mass over a solid-volume estimate for hollow
or composite parts. Use `Inertial.from_geometry(...)` for a primitive when its
mass is known. Let the SDK derive unresolved mass properties only when the
collision geometry is a reasonable proxy for material distribution.

Useful construction fill-factor priors for sanity checking are:

| Construction | Bounding-box fill factor |
| --- | ---: |
| solid casting or block | 0.7-0.9 |
| dense machined assembly | 0.3-0.5 |
| thin panel or shell | 0.05-0.15 |
| hollow tube/frame | 0.01-0.05 |
| sheet-metal enclosure | 0.005-0.02 |

Do not encode fill factor as a collision scale. It is an estimation aid. A
future SDK estimator may consume it explicitly; today use it to sanity-check or
choose an explicit mass.

## Passive Joint Dynamics

`MotionProperties` expresses passive joint behavior:

```python
motion_properties=MotionProperties(
    damping=0.3,
    friction=0.1,
    stiffness=40.0,
    equilibrium=0.0,
)
```

Units:

| Joint | Damping | Friction |
| --- | --- | --- |
| revolute/continuous | N*m*s/rad | N*m |
| prismatic | N*s/m | N |

`stiffness` uses N*m/rad for angular joints and N/m for prismatic joints.
`equilibrium` uses radians for angular joints and meters for prismatic joints.

Choose values by mechanism and scale rather than copying one value everywhere:

- Cabinet and appliance doors normally have hinge damping and bearing/seal
  friction.
- Drawers normally have rail friction and linear damping; soft-close behavior
  is more than a constant damper and should not be claimed unless modeled.
- Knobs and valves normally have rotational friction; spring return should be
  modeled separately when the SDK surface supports it.
- Deliberately free wheels or bearings should use explicit zeros.
- A gravity-loaded door that should remain closed needs a closed-side preload
  (`stiffness` plus `equilibrium`) and/or supported static friction. Damping
  alone only resists motion after the door has started moving.

### Gravity-sensitive folding doors

Use this procedure only for a door or flap whose closed pose tends to open or
drop under gravity and which should require an external force to open:

1. Estimate the gravity torque, `tau_g ≈ mass * 9.81 * horizontal_lever_arm`.
2. Set `equilibrium` on the closed side and choose a preload slightly above
   `tau_g` (roughly 1.1–1.3×) with `stiffness`.
3. Set `MotionLimits.effort`/USD `maxForce` near the preload, rather than far
   above it. This preserves an external breakaway force and limits rebound at
   large angles.
4. Use damping to limit opening speed; it does not provide static support.

This fixed target-drive approximation still produces some return torque after
the door is opened. Completely disabling the return force after breakaway
requires a runtime detent/latch state machine and should not be inferred for
assets that do not have this behavior.

OpenUSD export maps damping and stiffness to standard `PhysicsDriveAPI`: angular
for revolute/continuous joints and linear for prismatic joints. With a nonzero
stiffness and equilibrium, the drive provides a passive restoring torque. URDF
exports damping and friction through `<dynamics>`; stiffness/equilibrium are
preserved only in USD because core URDF has no equivalent field. OpenUSD Physics
does not define a portable Coulomb joint-friction attribute, so Articraft
preserves that value as `articraft:jointFriction`.

## Fallback And Diagnostics

The following are intentional and distinct:

- `physics_material=None`: use the generic material fallback and warn.
- `motion_properties=None`: dynamics are unresolved and movable joints warn.
- `MotionProperties(damping=0.0, friction=0.0)`: explicitly free joint; no
  missing-dynamics warning.
- `inertial=None`: derive mass properties from collision geometry and density;
  exported USD records `articraft:inertialSource="estimated_collision"`.

Warnings are non-blocking so old models remain compilable. Resolve them when
the object semantics provide enough evidence; do not silence them with invented
precision.

## Export Matrix

| Parameter | OpenUSD | URDF |
| --- | --- | --- |
| mass, center of mass, inertia | `PhysicsMassAPI` | `<inertial>` |
| density | `PhysicsMaterialAPI` | resolved into mass properties |
| static/dynamic friction, restitution | `PhysicsMaterialAPI` | no core representation |
| joint axis and bounds | physics joint schemas | `<axis>`, `<limit>` |
| viscous damping | `PhysicsDriveAPI` | `<dynamics damping>` |
| Coulomb joint friction | `articraft:jointFriction` metadata | `<dynamics friction>` |

For revolute/continuous joints, `MotionLimits.effort` is exported as the USD
drive `maxForce`; in URDF it is the joint `<limit effort>` field. It limits the
drive/actuator output and is not itself a static-friction model.

Do not add `PhysxSchema` fields to portable model authoring. Engine-specific
adapters may consume extra metadata in later stages.
