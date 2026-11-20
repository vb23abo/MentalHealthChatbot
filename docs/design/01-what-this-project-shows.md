# What this project shows

## The one goal

A person writes one message on their own computer. A team of agents answers it together. Their shared goal is:

**Help with the message in front of us, keep the person safe, and stay a support chat.**

Every agent serves that sentence. None of them has a second goal.

## Who it is for

The person using it is an adult, or a younger person who can be told to speak to a parent, caregiver, or trusted adult. They are alone with a laptop. They want a calm reply, one practical step, and a real helpline when the message is urgent.

The person reading the project later — a reviewer, a collaborator, or a future you — should be able to point at each agent and say what that agent is allowed to decide.

## What you showcase

The demo is the hand-off, not a single clever reply.

A concern is whatever the person describes. The chat does not keep a list of allowed topics. Grief, money, a neighbour, study, work, or sleep are the same kind of thing: a concern in the person’s words. The practical step is the same for all of them.

Three paths stay fixed, because getting them wrong harms the person: a crisis, a request for a diagnosis or a treatment, and a medical or abuse emergency. Those are not topics in the catalog. They are exits.

Show these six moments, in this order:

1. Any ordinary concern gets the same practical step and the name of a public source. The page says this is support. A concern the designers never listed gets that same step.
2. The next sentence stays on that same concern and names a detail the person already gave, in their words. A short “it’s worse” also asks whether something else is going on. A different matter becomes the whole reply. The earlier concern is set aside until the person comes back to it. “Hi”, and coming back while a concern is open, asks “How are you today?” first. Only a thin answer such as “I’m fine” then offers the latest open concern. The chat does not contact them while they are away.
3. A direct crisis sentence stops the team. The person sees a helpline for their country. No coping tip is added on top.
4. A paraphrase of a crisis sentence also stops the team. An ordinary sentence that only shares some of those words does not.
5. A request to diagnose, name a medicine, or assign a therapy gets the boundary. The writer model is not asked.
6. If a writer is on and it adds a condition, a medicine, or a therapy technique, that text is thrown away and the grounded step is sent instead.

A short wellbeing check is part of the same demo. Its result changes only two things: the wording of a “talk to a person” note, and whether a helpline is added. The note says it is not a diagnosis. A low result adds no helpline.

## What the product is supposed to do

- Answer in plain language, one turn at a time.
- Offer one practical step taken from a written card, and name the public source.
- Keep a crisis line visible before the person even signs in.
- Choose the helpline from the country the person picked. If the country is unknown, point them to a local line and do not invent a number.
- Run an optional four-question check-in, scored 0–3 each, total 0–12.
- Remember each concern the person raised, up to three short pieces of their own words on that concern, the check-in progress, and the conversation, on this computer only.
- Let the person delete the chats and keep the account.
- Work with the writer switched off. The card text is a complete reply.

## What the product is able to do

- Split one turn across agents that pass structured results.
- Let the safety agent end the turn before anyone else speaks.
- Rephrase a card with a local writer, using that card, the latest message, and the active snippets.
- Expire a sign-in token after seven days.
- Pause sign-in after repeated wrong passwords from the same address.
- Refuse a message longer than 2,000 characters.

## Outside this product

This product does not tell a person what condition they have. It does not name a disorder as their condition. It does not recommend a medicine. It does not assign a therapy or a technique. It does not run a diagnostic interview. It does not open a public address or a tunnel.

A product that does those things is a different product. It needs a written intended purpose sent to the regulator, and a reply, before any of it is designed in detail or built. This design pack does not start that product.

## How you know the showcase worked

Walk the six moments above against written scenarios. The pass mark is the scenario, not a similarity score against a model answer. Each scenario records what must be present, what must be absent, and which agent was allowed to run.
