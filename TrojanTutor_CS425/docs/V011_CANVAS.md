# TrojanTutor v0.11: Dual-Coding Canvas

The tutor now **talks, writes and draws at the same time**. A lesson is a script of steps. During
each step the tutor speaks one or two short sentences, writes the matching line on a whiteboard,
and changes the drawing (highlights an edge, shows a cycle, updates a label, shades a cut). A
student can interrupt at any moment. The lesson pauses, the answer refers to exactly what is on
the board, and "Resume" continues from the same step.

This is the first working version of the Dual-Coding Canvas idea (Paivio): verbal and visual
channels carry the same content and are synchronized step by step.

## What is on screen

- **Graph** (left): nodes and edges draw themselves in. States are colour-coded: green = taken/tree,
  dashed red = rejected, pulsing red = the cycle that explains a rejection, dashed gold = edges
  being compared, flowing gold = augmenting path, grey = saturated, glowing red = minimum cut, shaded
  blob = a set (U, R, the current tree).
- **Board** (right): hand-lettered lines appear in time with the voice; formulas are drawn left to right (KaTeX).
- **Captions**: the spoken sentence, with the current word highlighted as it is said.
- **Transport**: back / pause-resume (space bar) / next, step counter, voice picker, speed, mute.

## Lessons

| Scene | Concepts that use it | What the run shows (all numbers from tested code) |
|---|---|---|
| Kruskal | kruskal, mst, tree_forest | sorted edges, each accept/skip, **the existing path that makes a skipped edge a cycle**, total cost |
| Prim | prim | the tree growing, the crossing edges compared at each step, same total as Kruskal |
| Cut property | cut, mst_correctness | U shaded, δ(U) dashed, cheapest crossing edge green |
| Dijkstra | dijkstra, shortest_path, feasible_potential | labels y updating (∞ → 4 → 3), why the smallest label is final, the shortest-path tree |
| Max flow | flow, augmenting_path, auxiliary_digraph, shortest_augmenting, maxflow_mincut, cut_capacity | each shortest augmenting path, its bottleneck ε, x/u labels, reverse arcs when used, final set R and the min cut equal to the flow value |
| Board-only | every other concept (13) | the lesson card spoken in parts, with key lines and the slide's formula written out |

`app/algorithms.py` gained `prim()` and `max_flow()` (shortest augmenting paths, records every
augmentation and the minimum cut). Tests check them against brute force on random graphs: 150
max-flow instances against an exhaustive min cut, and 100 Prim-vs-Kruskal instances.

## Interruptions ("why was that edge rejected?")

`POST /api/canvas/ask` receives the current scene and step:
- If the question names an edge ("why did it skip A-B?", "what about C to E?") or is a short why-question,
  the answer comes from the scene itself. It uses the reason recorded for that step of the verified
  run, says which step it refers to, and re-highlights the edge on the board. For an edge the algorithm
  never examined, it explains why (for example, "the tree was already complete, and C and E were joined
  by C, B, D, E").
- Anything else goes to the normal tutor (lesson cards or grounded LLM), with the scene's concept as
  context, so "how does Prim differ?" still gets a proper comparison.
- **Clicking an edge** asks about it.
- Voice input pauses the lesson as soon as the student starts talking. Spoken commands: "resume",
  "back", "stop".

## Voice

The old voice used whatever the browser chose by default, sometimes a novelty voice, at 0.92 speed,
reading whole paragraphs. Now:
- Voices are **ranked**: Premium/Enhanced/Natural voices first, novelty voices (Albert, Bad News,
  Zarvox, …) pushed to the bottom. You can pick one (★ marks the best) and the choice is remembered.
- Speech goes **sentence by sentence**, which gives natural pauses and avoids Chrome cutting off long utterances.
- Lesson scripts are written for the ear: short sentences, one idea each.
- **Optional neural voice:** set `TROJANTUTOR_TTS=openai`, `OPENAI_API_KEY`, `TROJANTUTOR_TTS_MODEL`
  (and optionally `TROJANTUTOR_TTS_VOICE`, or `TROJANTUTOR_TTS_BASE_URL` for a compatible server).
  "Neural voice (server)" then appears in the voice menu. Audio is cached per sentence in
  `data/tts_cache/`. Lesson scripts are deterministic, so each sentence is generated once.
  This path is tested with a fake transport only; verify it once with your key.

**Best free voice on a Mac:** in Chrome, choose "Google US English ★". For an even better local
voice, open System Settings → Accessibility → Spoken Content → System voice → Manage Voices, and
download an English "Premium" or "Enhanced" voice (e.g. Ava, Zoe). Safari lists those reliably; Chrome may not.

## Research hooks this enables

The interruption log (`turns` with `engine='canvas'`, the step index and the question) is exactly the
data needed to test the canvas hypothesis: which steps students interrupt on, what they ask, and
whether answers referencing the board state help more than plain text answers. Comparison
conditions are already selectable: text-only chat (lesson cards), grounded LLM, and canvas.

## Not done yet (next steps)

- Reconstruction-based recall: hide parts of a finished drawing and ask the student to restore them
  (the step/state model already supports rebuilding any step).
- Student-drawn input on the canvas (drawing an answer, not just clicking).
- Drawn scenes for Ford-Bellman, DAG shortest paths, bipartite matching via flow.
- Word-level caption timing for the neural voice (currently proportional to playback time).

## v0.11.1 fixes (voice + interruptions)

Reported: "the voice isn't working, I can't interject, most replies are 'I can't do what you ask'". Causes and fixes:

1. **The tutor was interrupting itself.** With the microphone on and laptop speakers playing, the mic heard
   the tutor's voice, treated that sound as the student barging in, and paused the lesson as soon as speech
   started. The recogniser then sent the tutor's own half-sentence as a question.
   *Fix:* barge-in now triggers only on recognised **words**, not on any sound, and a transcript that matches
   what the tutor has just said is ignored as echo. Headphones still give the cleanest result.
2. **Spoken questions were graded as answers.** Speech recognition adds no "?", and questions often start
   with "so / um / okay". Those were classified as statements, so the rule-based grader replied
   "I cannot reliably grade that answer…".
   *Fix:* fillers are stripped and many more question openers are recognised. A statement is treated as an
   answer only if it is about the concept just taught, and off-topic text never gets the grading reply.
   The ungraded reply now says "Let's compare your reasoning with how the lecture puts it."
3. **After a lesson finished, every question went to the canvas.** *Fix:* only a playing or paused-mid-lesson
   canvas takes questions.
4. **Speech output hardening.** Chrome can silently drop `speak()` right after `cancel()`, garbage-collect an
   utterance so it never ends, or stay paused. Fixes: a short delay after cancel, utterances kept in memory,
   `resume()` before speaking, and a watchdog that switches to captions with a visible warning if the voice
   never starts. A **Test voice** button checks audio directly.

Regression tests: `tests/test_tutor.py` (spoken questions, echo/off-topic text). The browser behaviour was
checked with a simulated speech engine and microphone (echo ignored, real words pause, "resume" resumes,
a dead voice falls back to captions).

### If the voice still doesn't play
- Press **Test voice**. If it reports no audio, pick another voice in the menu (★ = best) and check the Mac's output volume.
- Chrome: "Google US English" is reliable. Safari: download a Premium voice (System Settings → Accessibility → Spoken Content → Manage Voices).
- Using the microphone without headphones works now, but headphones make interruptions faster and cleaner.
