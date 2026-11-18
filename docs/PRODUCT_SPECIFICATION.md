# MOTIONFORGE — Product Specification

## 1. Product vision

MOTIONFORGE is an Android-first training companion that combines realistic 3D demonstrations, camera-based movement tracking, and structured workout/fighting-fundamentals lessons.

It helps people understand what a movement should look like, practise it at their own pace, and receive limited, transparent feedback on selected visible movement patterns.

### Positioning

"See the movement. Practise it. Understand your progress."

MOTIONFORGE is not:
- A medical device.
- A physiotherapy tool.
- A replacement for a qualified personal trainer or martial arts instructor.
- A sparring or combat simulator.
- A guarantee of correct technique or injury prevention.

## 2. Target users

### Primary
- Beginners who want structured at-home fitness.
- People who want to learn basic boxing movement safely without sparring.
- Users who benefit from visual demonstrations and simple progress records.

### Secondary
- People who already train and want a convenient practice companion.
- Users who want short, guided sessions without a gym.

### Excluded from initial targeting
- Children.
- Users seeking rehabilitation or medical exercise plans.
- Competitive fighters seeking advanced technical analysis.
- Users training with weapons, contact sparring, or high-risk techniques.

## 3. User problems

1. Text descriptions are difficult to translate into body movement.
2. Exercise videos often do not explain what to look for.
3. Beginners may not know whether their body is visible to the camera.
4. People struggle to maintain a consistent, structured routine.
5. Basic training progress can be hard to track.

## 4. Product pillars

### A. 3D Coach
- Realistic trainer avatar.
- Front, side, and optional rear views where relevant.
- Pause, replay, and slow-motion controls.
- Step-by-step movement phases.
- Short verbal/text cues.
- Common mistakes and safer alternatives.
- No need to use a 3D avatar for every screen.

### B. Motion Coach
- Camera-based body landmark estimation.
- Live framing guidance.
- Supported movement detection.
- Basic repetition counting only where reliable.
- Rule-based feedback.
- Confidence and tracking-quality state.
- No unsupported claims about force, speed, impact, joint loading, or injury risk.

### C. Training plans
- Beginner pathways.
- Short sessions, approximately 5–20 minutes.
- Rest periods and warm-up prompts.
- User-controlled difficulty.
- Clear stop/pause control.
- No pressure-based streak design.

### D. Progress
- Completed sessions.
- Session duration.
- Repetition counts where reliable.
- Self-reported effort.
- Consistency trends.
- No body-weight, body-fat, or health tracking required for MVP.

## 5. Information architecture

Bottom navigation:
1. Home
2. Train
3. Progress
4. Profile

### Home
- Welcome message.
- Continue last programme.
- Suggested short session.
- Training categories.
- Safety reminder.

### Train
- Fitness
- Fighting Fundamentals
- Beginner programmes
- Exercise/lesson catalogue
- Filters by duration and difficulty

### Lesson detail
- Lesson title and purpose.
- Required space/equipment.
- Safety notes.
- 3D demonstration.
- Instructions.
- Common mistakes.
- Start practice.

### Live session
- Camera preview.
- Skeleton/landmark overlay toggle.
- Tracking status.
- Current exercise.
- Repetitions or timer.
- Feedback cue.
- Pause and stop.
- Camera positioning instructions.

### Session summary
- Exercises completed.
- Duration.
- Repetitions only if valid.
- Feedback encountered.
- Self-reported difficulty.
- Save session.

### Progress
- Weekly session count.
- Minutes trained.
- History.
- Programme progress.
- Personal notes.

### Profile/settings
- Units.
- Camera privacy explanation.
- Permission status.
- Data export/deletion.
- Account and sync settings.
- Subscription settings (later).

## 6. MVP experience

### First launch
1. Welcome and product explanation.
2. Age confirmation: MVP is intended for adults 18+.
3. Safety disclaimer.
4. Choose Fitness or Fighting Fundamentals.
5. Choose beginner goal.
6. Enter home screen.
7. No account required.

### First training session
1. Select a lesson.
2. Read the short safety/setup note.
3. Watch 3D demonstration.
4. Start camera setup.
5. Explain camera processing and privacy.
6. Request camera permission.
7. Confirm full body/required joints are visible.
8. Run a brief neutral calibration.
9. Begin guided practice.
10. Provide conservative feedback.
11. End session and show summary.

## 7. MVP content

### Fitness
- Bodyweight squat: full supported camera feedback after validation.
- Push-up: supported only with side-view setup; otherwise demo-only.
- Hip hinge: demo and guided practice only in MVP until rules validated.
- Standing mobility warm-up: guided, not scored.

### Fighting Fundamentals
- Boxing stance: guided positioning and basic landmark feedback.
- Jab: demonstration and limited movement-phase feedback.
- Cross: demonstration and limited movement-phase feedback.
- Guard return: simple guided feedback.
- Forward/backward footwork: timer and instructional cues, no automatic quality score.

### Excluded from MVP
- Kicks and spinning techniques.
- Grappling, throws, takedowns.
- Sparring.
- Contact drills.
- Weapons.
- Punch force measurement.
- Impact prediction.
- Advanced style identification.
- Automatic injury or risk prediction.

## 8. Monetization

Do not implement payment in the first functional prototype.

Proposed future model:
- Free: small starter catalogue, 3D demonstrations, limited sessions.
- Premium: complete programmes, expanded exercise library, progress insights, additional coach voices/visual themes.
- No paid claim of medical safety or guaranteed technique correctness.

Pricing hypothesis to test:
- Premium: €7.99–€12.99/month.
- Annual plan only after retention and willingness to pay are validated.

## 9. Success metrics

Prototype:
- Users can complete onboarding without assistance.
- Camera setup succeeds on tested devices.
- At least 80% of test sessions can identify whether tracking is usable (internal target, validate).
- Feedback is understandable and not misleading.
- No critical crashes in tested core flows.

Early product:
- Activation: first completed session.
- D1/D7 retention.
- Sessions per active user per week.
- Programme completion.
- Camera setup abandonment.
- Tracking failure rate.
- User-rated usefulness of feedback.
- Refunds/churn if paid.

Do not optimize for time spent in app. Optimize for safe, useful training sessions.
