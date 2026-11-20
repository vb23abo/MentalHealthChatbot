# Support chat

A mental health chatbot should help someone talk through what they feel, notice when they may be in danger, and point them toward a person who can actually assess them. It should not diagnose, name a therapy as their treatment, or prescribe.

## Agents

Four task agents handle one message, in this order. They are not separate clinicians, and they do not diagnose.

1. **Safety** reads the new message. The phrase list runs first. A second local check can add the crisis line when that list misses the wording, including when it is unsure. It cannot remove a line the phrase list already returned.
2. **Check-in** runs the four questions only if the person asked, and writes the clinician note after a high result.
3. **Support** writes the listening reply from a local card: one practical step and a public source for sleep, worry, panic, sadness, loneliness, anger, or talking with a clinician. The local model, when it is on, may only rephrase that card. If it drops the practical step, the card text is sent. A request for a diagnosis does not open a card.
4. **Memory** saves the account, the recent turns, the last topic, and the safety flag after the reply is chosen. A sign-in token expires after seven days. Five wrong passwords from one address pause further sign-in attempts.

## How a message is handled

1. **Safety, before any other reply.** Self-harm, violence, a possible medical emergency, and abuse each stop the conversation and return resources. The phrase list runs on the raw new message. A second local check can add the crisis line for wording the list missed, and for a shorter stem it is not sure about. It cannot clear a phrase-list match. The crisis line stays on the page before sign-in. The default is 988 in the US. A country choice switches that number, and a country that is not listed keeps the IASP directory. The page says the chat is for adults, and where a young person should go instead.
2. **Check-in, only if they ask.** Four original questions about the last two weeks, scored 0–12 and described as low, moderate, or high. The result says it is not a diagnosis. A high result adds a note they can copy for a clinician: sleep, mood, how long, what was hardest, and the band, taken from this chat. The note is saved with the account until they delete saved chats. A low result does not add crisis resources.
3. **Support reply.** One concern at a time. The reply echoes a short piece of what they just said, then the card for that concern: one practical step, when to talk with a doctor or counselor, and the public source. The card says it is support. A later message stays on that concern until they bring up a new one. A local model can rephrase the card. Safety, a check-in, and a crisis reply never go to the model. If the model is off, fails, writes a diagnosis or a medication, or leaves out the practical step, the card text is used.
4. **Boundary on every reply.** The assistant is a support tool, not a clinician.

An account is a username and a password. The password is stored as a hash. A sign-in token is stored as a hash and expires after seven days. Five wrong passwords from the same address pause sign-in for 15 minutes. A message longer than 2,000 characters is refused. The server log records the path and the status, not the message text. Recent messages, the last topic, the check-in in progress, and a safety flag are stored in `data/support.sqlite` on this computer. Messages older than 30 days are deleted, and only the latest 30 turns are kept. There is no disorder name in the database. Delete saved chats removes the messages and the summary. Sign out keeps them for the next visit. The app listens on 127.0.0.1.

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
