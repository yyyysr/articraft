# Testing And Quality Checks

## Purpose

Use `TestContext` to verify object-specific structure, placement, motion, and
clearance. Tests should prove the authored intent rather than merely restate
that compilation succeeded.

```python
ctx = TestContext(object_model)
return ctx.report()
```

`TestReport` contains failures, warnings, and allowed QC exceptions. Use
`ctx.check(name, ok, details="")`, `ctx.fail(name, details)`, and
`ctx.warn(text)` for conditions not covered by an exact assertion.

## Pose Checks

```python
with ctx.pose({articulation: position}):
    ...
```

Joint keys may be articulation objects or names. Revolute/continuous positions
are radians and prismatic positions are meters. Test decisive poses such as
closed and open limits when geometry or attachment behavior changes with
motion.

World-space queries include:

```python
ctx.part_world_position(part)
ctx.link_world_position(link)
ctx.part_world_aabb(part)
ctx.link_world_aabb(link)
ctx.part_element_world_aabb(part, elem=visual_or_collision)
```

## Exact Assertions

```python
ctx.expect_origin_distance(
    link_a, link_b, *, axes="xy", min_dist=0.0, max_dist=None, name=None
)
ctx.expect_origin_gap(
    positive_link, negative_link, *, axis, min_gap=0.0, max_gap=None, name=None
)
ctx.expect_contact(
    link_a, link_b, *, contact_tol=1e-6, elem_a=None, elem_b=None, name=None
)
ctx.expect_gap(
    positive_link, negative_link, *, axis,
    min_gap=None, max_gap=None, max_penetration=None,
    positive_elem=None, negative_elem=None, elem_a=None, elem_b=None, name=None,
)
ctx.expect_overlap(
    link_a, link_b, *, axes="xy", min_overlap=0.0,
    elem_a=None, elem_b=None, name=None,
)
ctx.expect_within(
    inner_link, outer_link, *, axes="xy", margin=0.0,
    inner_elem=None, outer_elem=None, elem_a=None, elem_b=None, name=None,
)
```

Element-specific arguments target a named visual or collision and are preferred
when whole-part AABBs include unrelated geometry. Use world AABB assertions for
coarse spatial intent and contact queries for actual geometry contact.

## Structural Checks

```python
ctx.fail_if_articulation_origin_far_from_geometry(
    *, tol=0.015, reason=None, name=None
)
ctx.warn_if_articulation_origin_far_from_geometry(
    *, tol=0.015, reason=None, name=None
)
ctx.warn_if_coplanar_surfaces(
    *, max_pose_samples=32, plane_tol=0.001,
    min_overlap=0.02, min_overlap_ratio=0.35,
    ignore_adjacent=True, ignore_fixed=True, name=None,
)
```

Choose tolerances from object scale and the intended fit. A broad tolerance that
makes every configuration pass is not evidence.

## QC Allowances

```python
ctx.allow_overlap(
    link_a, link_b, *, reason, elem_a=None, elem_b=None
)
ctx.allow_isolated_part(part, *, reason)
ctx.allow_coplanar_surfaces(
    link_a, link_b, *, reason, elem_a=None, elem_b=None
)
```

Allowances document intentional geometry; they do not repair bad topology.
Scope an allowance to exact elements when possible and give a mechanical
reason. Do not broadly allow all overlap between two large parts to hide an
unknown intersection.

An isolated part allowance is appropriate only when disconnected geometry is
intentional, such as a nonphysical annotation. A physical mount should be
modeled as connected or articulated geometry instead.

## High-Signal Test Selection

- Check required parts and articulations by stable names.
- Verify axis direction and limits through pose-dependent geometry, not only
  stored scalar values.
- Check clearances at poses where collision is most likely.
- Verify intended containment, contact, or retained insertion at the relevant
  local elements.
- Keep tests independent of incidental triangulation and materialized filenames.
- Use probe tooling to inspect uncertain state before adding a permissive
  allowance.
