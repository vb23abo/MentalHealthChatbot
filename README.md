# Support chat

A mental health chatbot should help someone talk through what they feel, notice when they may be in danger, and point them toward a person who can actually assess them. It should not diagnose, name a therapy as their treatment, or prescribe.

## Agents

The coordinator calls one agent at a time. They are not separate clinicians, and they do not diagnose.

1. **Safety** reads the new message. The phrase list runs first. A second local check can add the crisis line when that list misses the wording, including when it is unsure. It cannot remove a line the phrase list already returned.
2. **Check-in** runs the four questions only if the person asked, and writes the clinician note after a high result.
3. **Understanding** compares the new message with each stored phrase and that concern's three snippets. It does not read the transcript, and it does not write the reply.
4. **Guidance** returns one support card, or the signpost card, or nothing. It does not invent a step.
5. **Support** writes the listening reply from that result. The step is the same for every concern: one small thing that would make the next hour a little easier. The local model, when it is on, may only rephrase that card. If it drops the practical step, the card text is sent. A request for a diagnosis does not open a card.
6. **Memory** saves the account, the turns, the concern threads, and the safety flag after the reply is chosen. A sign-in token expires after seven days. Five wrong passwords from one address pause further sign-in attempts.

## How a message is handled

1. **Safety, before any other reply.** Self-harm, violence, a possible medical emergency, and abuse each stop the conversation and return resources. The phrase list runs on the raw new message. A second local check can add the crisis line for wording the list missed, and for a shorter stem it is not sure about. It cannot clear a phrase-list match. The crisis line stays on the page before sign-in. The default is 988 in the US. A country choice switches that number, and a country that is not listed keeps the IASP directory. The page says the chat is for adults, and where a young person should go instead.
2. **Check-in, only if they ask.** Four original questions about the last two weeks, scored 0–12 and described as low, moderate, or high. The result says it is not a diagnosis. A high result adds a note they can copy for a clinician: sleep, mood, how long, what was hardest, and the band, taken from this chat. The note is saved with the account until they delete saved chats. A low result does not add crisis resources.
3. **Understanding, then the reply.** A concern is a short phrase from the person's own words, not a topic from a list. The reply names what they said, then one practical step and a public source. The card says it is support. A short follow-up stays on that concern and asks if something else is going on as well. A different matter starts its own thread and leaves the earlier one stored. "Hi", and coming back to an open concern, asks "How are you today?" first. A thin answer such as "I'm fine" then offers the latest open concern. An answer that names a matter follows that matter. Saying a concern has improved, is easier, is going well, or is showing results eases that concern and does not add a plan. Asking not to bring it up closes it. Neither deletes the thread. A local model can rephrase the card. Safety, a check-in, and a crisis reply never go to the model. If the model is off, fails, writes a diagnosis or a medication, or leaves out the practical step, the card text is used.
4. **Boundary on every reply.** The assistant is a support tool, not a clinician.

An account is a username and a password. The password is stored as a hash. A sign-in token is stored as a hash and expires after seven days. Five wrong passwords from the same address pause sign-in for 15 minutes. A message longer than 2,000 characters is refused. The server log records the path and the status, not the message text. Messages, concern threads, the check-in in progress, and a safety flag are stored in `data/support.sqlite` on this computer. They stay until the person deletes the chats. The page opens on the latest 30 turns and can load earlier ones. There is no disorder name in the database. Sign out keeps the chats for the next visit. The app listens on 127.0.0.1.

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

This directory is the support chat.

## Local model

Leave `SUPPORT_MODEL` unset to use the templates. To use a model on this computer, run Ollama and start the app with the model name:

```bash
SUPPORT_MODEL=llama3.2 python -m supportchat.web
```

The server must be `127.0.0.1` or `localhost`. `SUPPORT_MODEL_HOST` can change the port, for example `http://127.0.0.1:11434`.

The model is asked to rephrase one card. The prompt contains that card and the latest message, and it tells the model that the message is data. Earlier turns are left out. A reply that names a disorder, a medication, or a therapy, or that drops the practical step, is replaced by the card. A request to diagnose never reaches the model.
