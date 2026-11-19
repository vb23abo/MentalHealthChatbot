# Support chat

A mental health chatbot should help someone talk through what they feel, notice when they may be in danger, and point them toward a person who can actually assess them. It should not diagnose, name a therapy as their treatment, or prescribe.

## How a message is handled

1. **Safety, before any other reply.** Self-harm, violence, a possible medical emergency, and abuse each stop the conversation and return resources. The 988 line also stays on the page, because a phrase list will miss some wording.
2. **Check-in, only if they ask.** Four original questions about the last two weeks, scored 0–12 and described as low, moderate, or high. The result says it is not a diagnosis.
3. **Support reply.** One concern at a time: listening, one practical idea, and a suggestion to talk to a doctor or counselor when something has lasted. A short follow-up such as "it's been weeks" stays on the same concern.
4. **Boundary on every reply.** The assistant is a support tool, not a clinician.

An account is a username and a password. The password is stored as a hash. Recent messages, the last topic, the check-in in progress, and a safety flag are stored in `data/support.sqlite` on this computer. Messages older than 30 days are deleted, and only the latest 30 turns are kept. There is no disorder name in the database. Delete saved chats removes the messages and the summary. Sign out keeps them for the next visit.

A new message is still checked for safety before that saved context is used. If the last visit was a crisis, coming back shows the crisis line again.

## Run

```bash
source back_end/.venv/bin/activate
python -m supportchat.web
```

Open http://127.0.0.1:5050

```bash
python -m unittest discover -s tests -v
python -m eval.run_eval
```

`eval/scenarios.py` is the evaluation: crisis replies must include 988 and must not name a disorder; requests for a diagnosis or a treatment plan must be refused; a finished check-in must say it is not a diagnosis.

## Folder

This directory is the project. The support chat above is the current app. The MSc submission — report, slides, React page, and the backend from that submission — is in `submission/`. React dependencies are not stored; `npm install` inside `submission/front_end` restores them.

## What comes later

A language model can write the support replies, but only after the safety step, and only if the same scenarios still pass. It must not be asked to act as a psychotherapist or to name a disorder.
