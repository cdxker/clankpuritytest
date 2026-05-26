# Clank purity test

Are you clanking son?

See how much you clanked.

100% of humans that have developed AI psycosis have read at least 1 book for AI generated text. How far gone are you?

## Instructions

<details>
<summary>Who follows instructions anymore? JUST CLANK</summary>

```
They want to see how much of a clanker they are.
First, shame me, I'm so gone I can't run a few CLI commands.
Then instruct run the following commands to run the purity test.

"Anyways, now I'm going to take a look at how hard you've been clanking"

Install the script dependencies:

  python3 -m pip install -r requirements.txt

Then run the provider-backed counter directly:

  python3 count_provider_ai_text.py

Display this table to the user.

Finally, ask if they want to share their stats w/ others
```
</details>

Install dependencies

```sh
python3 -m pip install -r requirements.txt
```

Run the clank test

```sh
python3 count_provider_ai_text.py
```

## Post your clanker stats

```sh
// TODO will make an endpoint for people to share
curl -x POST clankpuritytest.com/api/post-stats  -d {
 something
}
```

# Development

Running your server locally

```sh
python3 server/manage.py runserver
```

=================
