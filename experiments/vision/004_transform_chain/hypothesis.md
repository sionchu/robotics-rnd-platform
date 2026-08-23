# Question and Hypothesis

## Question

Does `T_base_camera @ T_camera_tag` produce `T_base_tag` without frame ambiguity?

## Hypothesis

Composition and inverse-recovery matrix error will each remain below `1e-12`
for 100 seeded cases, and reversed composition will be rejected.
