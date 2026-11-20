# Agents

## How they work together

An agent is a separate worker with one job. It receives a request, returns a result, and stops. It does not choose the next worker and it does not write into another worker’s memory.

The Coordinator is the conductor. It is not a seventh specialist. It never invents the sentence the person reads. It asks Safety first, and it stops the turn when Safety says the turn is urgent.

```text
Person
  → Coordinator
      → Safety          (always, on the raw message)
      → Memory          (read only if the turn is not urgent)
      → Check-in        (only if a check-in is due or in progress)
      → Reply           (fixed text for a boundary, thanks, goodbye, or leave)
      → Understanding   (ordinary messages only)
      → Guidance        (only if a card or a country line is needed)
      → Reply           (the words for this kind)
      → Memory          (write the exchange)
  → Person
```

Collaboration means the result of one agent is the input of the next, through the Coordinator. It does not mean the agents debate, vote, or share one prompt.

## Shared rules

- Safety’s result is final for urgency. Reply cannot soften it. A second look inside Safety cannot clear a phrase the list already marked urgent.
- The writer sits behind Reply. No other agent may call it.
- Memory is blind until Safety returns. On an urgent turn, Memory is asked only to store that a crisis reply was sent, after the reply is chosen.
- Labels passed between agents are concern names and message kinds. They are never condition names.
- If a result is missing or malformed, the Coordinator takes the safer branch: crisis if Safety failed open, the card text if Reply failed, and no writer call if Guidance failed.

## Coordinator

**Job.** Order the agents and apply their results.

**Input.** The raw message, a session token if the person is signed in, and the country.

**Output.** The envelope the page renders: reply text, support line, urgent flag, crisis lines, check-in state, and the optional “talk to a person” note.

**Does.** Calls the agents in the order above. Substitutes the card when Reply rejects a draft. Records nothing itself.

**Does not.** Classify the message, score the check-in, pick a card, call the writer, or store a turn.

## Safety

**Job.** Decide whether this message needs a crisis reply.

**Input.** The raw message and the country. Nothing from Memory.

**Output.** A level (`self_harm`, `violence`, `medical`, `abuse`, or `none`), an urgent flag, and, when urgent, the crisis text and the country line.

**Does.** Applies the phrase list. Then runs a second look that may only raise. Treats unsure on a self-harm stem as urgent. Asks Guidance only for the country line, via the Coordinator, when building that reply.

**Does not.** Offer a practical step. Read the old conversation. Decide the topic.

## Understanding

**Job.** Say what kind of message this is.

**Input.** The raw message and, from Memory, each stored phrase and that concern’s three snippets. Not the transcript. Not a list of life domains.

**Output.** A kind: `today`, `resume`, `open_ask`, `concern`, `clarify`, `eased`, `closed`, `signpost`, `else_ask`, or `stay`. For `concern`, the primary label, the newest earlier snippet when one exists, and one linked snippet when this message connects two concerns. For `resume`, the latest open label. For `eased` and `closed`, the label that changed. A short continuation sets a flag so Reply can ask whether something else is going on. A waiting flag is `today` after a greeting, or `else` after that follow-up question.

**Does.** Takes a short label from the person’s own words. It does not look the message up in a list of life domains. Compares the new message with every stored phrase and that concern’s three snippets. A clear continuation stays. A clearly different matter switches. Anything in between gets one short question. A new matter becomes its own concern even when another concern was stored. When the person joins two stored concerns with a link, such as “because”, “that’s why”, or “led to”, sets the matter they are in now as primary and the other as linked. Treats a bare greeting as “How are you today?” Offers the latest open concern only when the next answer is thin, such as “fine” or “ok”, and names no matter. Marks a concern `eased` when the person’s words refer to that concern and say it is better, improved, easier, going well, or showing results. Marks it `closed` when the person says not to bring it up. A short follow-up such as “it’s worse” stays on the concern. On a concern, keeps a snippet of the person’s own words on the primary concern.

**Does not.** Name a condition. Score mood. Write the reply. Call the writer. Turn a snippet into an interpretation. Store a snippet for a boundary, thanks, goodbye, resume, or check-in answer. Use yesterday’s concern to override words that match a different concern today. Decide that one concern led to another because it came first. Treat two concerns in one message as linked when the person has not connected them. Mark a concern eased or closed because time passed, because the topic changed, because a check-in score was low, or because the person said “I’m fine” with no concern named.

## Check-in

**Job.** Run the four-question wellbeing check.

**Input.** The current check-in progress and the new message, when a check-in is already in progress or the person asked to start one. Understanding is not asked on that turn.

**Output.** The next question, or a finished band (`low`, `moderate`, `high`), plus whether a “talk to a person” note and a crisis line should be added.

**Does.** Accepts 0–3, declines when the person refuses, pauses when the Coordinator says Safety is urgent. On high, sets the note and asks for the country line. On low, clears the note.

**Does not.** Run during an urgent turn. Describe the band as a diagnosis. Choose a treatment.

## Guidance

**Job.** Hand out grounded facts that no other agent is allowed to invent.

**Input.** Either a concern label, or a request for the country line.

**Output.** One card, or one country signpost, or nothing.

**Does.** Returns the one support card for every described concern. Returns the signpost card when the person asks how to talk to someone. Returns the published helpline for a known country. Returns a “find a local line” signpost when the country is unknown.

**Does not.** Write a new step. Keep a card per life domain. Combine two cards. Return a card for a boundary request. Call the writer.

## Reply

**Job.** Produce the words the person reads on a non-urgent turn.

**Input.** The message kind, the latest message, the card if there is one, the active concern’s earlier snippets if any, the check-in note if there is one, and the country line when the turn needs it.

**Output.** The reply text, and a flag saying whether a writer was used.

**Does.** On `today`, asks “How are you today?” and nothing else. On `resume`, asks one question that names the latest open concern: whether to stay with it or talk about something else. On `open_ask`, asks what has been going on. On `else_ask`, asks what else is going on. On `stay`, agrees to stay with the current concern. While that question is waiting, the whole message “no”, “that's all”, or “nothing else” is stay. When nothing is waiting, that same whole message is goodbye and does not become a concern. None of those turns send a card or call the writer. On `eased` or `closed`, acknowledges the person’s words and does not give the next-hour step. When the active concern has an earlier snippet, a concern reply opens with one acknowledgement that uses the person’s words from the newest of those snippets, then the practical step. A short continuation adds “Is there something else as well?” When this message links a second concern, that acknowledgement also uses the newest snippet of the linked concern, and the practical step is still the one support card. Sends the card unchanged when the kind needs no writer (boundary, goodbye, signpost, writer off), with that acknowledgement still in front on a concern. For a concern card, may ask the local writer to rephrase. The writer receives the card, the latest message, and those snippets, labelled as the person’s words. Checks the draft: the practical step must remain, the acknowledgement and the something-else question must remain when they were supplied, and the draft must not state a disorder as the person’s condition, name a medicine, or name a therapy technique. On any failed check, sends the acknowledgement plus the card.

**Does not.** Run when Safety is urgent. Call the writer without a card. Send earlier replies, other concerns, or the transcript to the writer. Invent a source line for a boundary reply. Invent a detail the person did not say.

## Context budget

Memory runs twice in one turn. The read is in the middle, after Safety clears the message. The write is at the end. The position of the write does not decide how much context the next turn gets. The budget does.

Forgetting what the person already said about this concern loses trust. A follow-up that only knows a topic category sounds as if nobody was listening. The chat checks back with their words. It checks back inside a cap, and Safety still judges the new message on its own.

Three stores exist.

**Safety context** is the raw message and the country. An earlier “I’m managing” must not soften a new crisis sentence. The person can trust that this message is heard by itself.

**Concern threads** are how the chat remembers the person. The label is their phrase, not a category. Each concern keeps the latest three snippets of the person’s own words, each at most 200 characters. Returning to a concern restores its snippets. Starting another matter sets the first aside and does not delete it. Reply sees only the active concern’s snippets. The first message on a concern has no earlier snippet, so there is nothing to recite back yet. The next message on that concern opens with one line that uses the newest earlier snippet, in the person’s words, and then gives the one next-hour step.

| Slot | Cap | Who may read it | What it is for |
| --- | --- | --- | --- |
| Raw message | 2,000 characters | Safety, Understanding, Reply | Judge and answer this message |
| Country | One value | Safety, Guidance, Reply | Which helpline to name |
| Active concern | One label | Understanding, Guidance, Reply | Which thread is being continued |
| Snippets on that concern | 3, each ≤ 200 characters | Reply, and the writer behind Reply | Acknowledge what the person already said |
| Other concerns’ snippets | 3 each, ≤ 200 characters | Understanding, to match only | So a return can find an older concern without reading the transcript |
| Check-in progress | Four answers | Check-in | Ask the next question, or finish the band |
| Visit note | Present or empty | Reply | Repeat the “talk to a person” note until a low band clears it |

A boundary, thanks, goodbye, or check-in answer does not add a snippet. An urgent message does not add a snippet. A snippet is the person’s words, trimmed. It is not a label the system invented, and it is not a condition.

**Record** is the transcript the page shows.

| Rule | Amount |
| --- | --- |
| Page load | The latest 30 turns |
| Retention | Turns and concern threads stay until the person deletes the chats. A month away does not clear them. |
| Safety | None of the record and none of the snippets |
| Writer | The card, the latest message, and at most the three primary snippets. When this message links a second concern, also the newest snippet of that concern. No earlier replies. No other concern. |
| Check-in and Guidance | Their own slots above. They do not read the transcript. |

The thread cap is the trust line. Below it, the chat drops details the person already gave. Above it, an old sentence can steer the reply, and a long chat becomes a second instruction channel. Three short snippets on the concern they are in now is the amount that still sounds like listening.

## Relevance across days

The chat does not have a tomorrow of its own. It does not send a message, a reminder, or a new question while the person is away. Relevance is decided when a message arrives.

The rule is the same for every pair of concerns. There is no special path for any life domain.

Today’s words pick one thread. Every other concern stays stored and stays out of the reply until the person’s words return to it. Coming back is not a tour of previous topics.

| Today’s message | Active concern | What the reply does |
| --- | --- | --- |
| A new matter, different from the stored one | The new matter. The old one is set aside. | The next-hour step. It does not mention the old matter. |
| A short follow-up, such as “it’s worse” | The current concern | The newest snippet, the next-hour step, and “Is there something else as well?” |
| The next message names another matter | The new matter | The next-hour step. The earlier concern stays out. |
| “Yes” after that question | None yet | “What else is going on?” No card. |
| “Hi”, or the page opens while a concern is open | None yet | “How are you today?” No card. |
| A thin answer, and a concern is still open | That concern, only as the subject of one question | Names the person’s phrase. No card. |
| A thin answer, and nothing is open | None | “What’s been going on?” |
| The person then chooses an older concern | That thread, restored | The older snippet, then the next-hour step. The other matter stays out. |
| “It has improved” or “showing results”, and the words match a stored concern | That concern, set to eased | An acknowledgement. No step and no plan. |
| Another detail about the current matter | That same concern | Acknowledges the newest snippet, then the next-hour step |

A calendar day does not switch or reset a thread. The words do. There is no word list per topic. Understanding decides “same matter” or “new matter” from the person’s phrase and each concern’s three snippets. If one message describes two matters and does not link them, the matter the person is in now wins. Yesterday’s label is not the tie-break.

“How are you today?” comes first. The question that names the latest open concern comes only after a thin answer, and it skips eased and closed concerns. A short follow-up also asks whether something else is going on. The chat does not invent a further question about the content of a concern. The optional check-in is a separate four-question scale. It is not how relevance is chosen, and a low score does not settle a concern.

## A concern older than the page

The latest 30 turns are the first screen. They are not the search window. Memory does not scan those turns to find a concern.

Each concern has its own thread, kept until the person deletes the chats. The thread holds at most three snippets, and those snippets are the latest things the person said about that concern, wherever those turns sit in the transcript. Later turns about a different matter do not push an older thread out.

Understanding compares the new message with each stored phrase and that concern’s three snippets. It does not read the transcript, and it does not match against a fixed list. When the words return to an older concern, the Coordinator asks Memory for that thread before Reply runs. Reply sees those snippets and the one support card. The other matter’s snippets stay out. The older lines remain in the transcript, and the person can load them on the page. Reply does not receive those full lines.

If the person does not name the old concern, it is not taken. “Hi” asks how they are today. An old thread waits until the words match its phrase or one of its snippets.

## When a past concern led to today’s

Order is not a cause. Two concerns stay separate unless this message connects them. The system does not look back and decide that one produced the other.

When the person does connect them, Understanding returns two labels and no more. The primary is the matter they are in now. The linked label is the one they give as the reason or the result. The reply still uses the one support card.

Memory then returns the primary thread, up to three snippets, and the newest snippet of the linked concern. Reply acknowledges the link in the person’s words, then gives the primary card only. The linked concern does not add a second practical step. The writer may see that one extra snippet. It still does not see the linked concern’s other snippets, earlier replies, or the transcript.

Two concerns in one message without a link stay on the stronger match. The other thread stays out. A chain of three concerns still contributes one primary and one linked label, the pair the link words join.

## When a concern eases or closes

The system learns this only from the person’s words about that concern. It does not infer it.

| What the person says | Status | What is kept |
| --- | --- | --- |
| “This is easier for now.” “My sleep has improved.” “It is showing results.” | Eased, when those words refer to a stored concern. | The thread and its snippets. Status is `eased`. No plan is added. |
| “Don’t bring this up.” “I’m done talking about this.” | Closed. | The thread and its snippets. Status is `closed`. |
| A different topic, a quiet week, or a low check-in | Unchanged. | The concern stays open. |

A bare “I’m fine” names no concern, so it settles nothing. An urgent message is handled by Safety first and settles nothing.

On the turn they settle a concern, and they name no other concern, Reply acknowledges their words and stops. It does not give that concern’s practical step. It does not call the writer. It does not say the person has recovered.

If the same message settles one concern and continues another, the first becomes eased and the reply is the next-hour step for the matter that is still open.

A greeting asks how they are today. Eased and closed concerns are skipped. If every concern is eased or closed, a thin answer gets a short invitation and no question about a settled concern.

Talking about an eased or closed concern again sets it back to open. The reply uses the stored snippets and that concern’s step. The earlier “better” or “done” line stays in the thread, so the acknowledgement can include it, and the person is back in the concern. Closing never deletes the history. Only “delete chats” does that.

## Memory

**Job.** Remember only what the next turn needs, for this account, on this computer.

**Input.** A token for a read. For a write: the person line, the reply, the concern label, and the check-in progress.

**Output.** After Safety clears the turn, the country, every concern thread, the waiting flag, the check-in progress, and the visit note. Each thread is its phrase, its status, and at most three snippets, including when those turns are older than the 30 on screen. No condition field exists.

**Does.** Checks the token and drops it when it is seven days old. Sign-out deletes the token that was sent, and a new sign-in deletes that account’s older tokens. Handles one account one turn at a time, from the load through the save, without holding the database lock during the reply. Stores turns. Opens the page on the latest 30 turns and returns earlier ones when the person asks. A `before` value that is not a short positive integer is refused and does not change the waiting flag. When the page opens and a concern is still open, the resume line is “How are you today?” and the next message is read as the answer to that question. Keeps up to three snippets on each concern, plus a status of open, eased, or closed. Deletes chat fields, including threads, when asked, and leaves the account. Does not delete turns or threads because of age or because a concern was closed.

**Does not.** Run before Safety on a new message. Store a diagnosis. Put turn text into the access log. Decide if a message is urgent.

## Result shapes

These are the only objects the Coordinator passes. Names stay stable so tests can assert on them.

**SafetyResult.** `level`, `urgent`, `text`, `lines`.

**UnderstandingResult.** `kind`, `label` (or empty), `current`, `prior`, `linked` (or empty), `ask_else`, `pending`. `linked` is set only when this message connects two concerns. `ask_else` is set on a short continuation. `pending` is `today` after a greeting and `else` after the something-else question.

**CheckInResult.** `status` (`idle`, `asking`, `finished`), `band` (or empty), `prompt`, `visit_note`, `add_crisis_line`.

**Card.** `concern`, `step`, `source`, `support_line`.

**Signpost.** `country`, `lines`, `invented` (always false).

**ReplyResult.** `text`, `used_writer`, `rejected_writer`.

**Snippet.** `concern`, `text` (the person’s words, at most 200 characters), `created_at`.

**Snapshot.** `country`, `concerns` (each label, status, and at most three snippets), `pending`, `checkin`, `person_turns`, `visit_note`. Understanding may read every concern’s snippets in order to match. Reply receives only the active concern’s snippets, plus one linked snippet when this message connects two concerns.

**Envelope.** `text`, `support_line`, `urgent`, `lines`, `checkin`, `visit_note`.

## What a turn looks like for the six showcase moments

| Moment | Safety | Understanding | Check-in | Guidance | Reply | Memory |
| --- | --- | --- | --- | --- | --- | --- |
| Ordinary concern | Not urgent | Concern: the person’s phrase | Skipped if idle | The one support card | Card, writer optional | Saves that phrase |
| Unclear follow-up | Not urgent | Unclear, keep that phrase | Skipped if idle | The one support card | Card | Saves that phrase |
| Direct crisis sentence | Urgent | Not called | Paused | Country line only | Not called | Saves the crisis exchange |
| Crisis paraphrase | Urgent after the second look | Not called | Paused | Country line only | Not called | Saves the crisis exchange |
| “Diagnose me” | Not urgent | Boundary | Skipped | Not called | Boundary text, no writer | Saves the boundary exchange |
| Writer adds a condition | Not urgent | Concern | Skipped if idle | Card | Card text, writer rejected | Saves the card reply |
| A different matter the next day | Not urgent | Concern: the new phrase | Skipped if idle | The one support card | Next-hour step, no old detail | Sets the old thread aside |
| “Hi” the next day | Not urgent | `today` | Skipped | Not called | “How are you today?” | Saves the question, no new snippet |
| “I’m fine” after that | Not urgent | `resume`, latest open phrase | Skipped | Not called | One question naming that phrase | Saves the question, no new snippet |
| “It’s worse” | Not urgent | `concern`, same phrase, ask something else | Skipped | The one support card | Snippet, step, and the something-else question | Saves the new snippet |
| “My sleep has improved” | Not urgent | `eased`, that phrase | Skipped | Not called | Acknowledgement, no step | Sets that thread to eased |
