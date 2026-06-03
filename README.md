# repafiller

CLI tool for filling and submitting attendance on milankoys.sk.

## Setup

```bash
git clone <repo>
cd repafiller
poetry install
```

Create a `.env` file in the project root:
```
REPA_TOKEN=token your_token_here
```

---

## Usage

### Build a template

Run the wizard to define which classes appear on each day of the week:

```bash
repafiller --wizard week_a
```

You will be prompted day by day (Monday → Friday). For each class enter the name and length separated by a space or semicolon:

```
── Monday ──
  How many classes? 2
  Class 1 (name length): ENG 2
  Class 2 (name length): PaS 1
```

Templates are saved to `templates/week_a.json`. Descriptions are left blank — they come from `inventory.txt`.

---

### Fill inventory.txt

Add descriptions for each subject. The script consumes them in order, one per appearance:

```
[ENG]
Reading comprehension exercises
Vocabulary and word formation
Grammar - past tenses review

[PaS]
Modules in Python
OOP basics
Working with files
```

---

### Save attendance

```bash
repafiller -m june -f week_a
```

With multiple alternating week templates:

```bash
repafiller -m june -f week_a,week_b,week_c
```

With leave days (days with no class — skipped entirely):

```bash
repafiller -m june -f week_a,week_b -l 5,6,25
```

Preview without sending:

```bash
repafiller -m june -f week_a,week_b -l 5,6 --dry-run
```

---

### Submit attendance

After saving, check the site looks correct then submit:

```bash
repafiller -m june --submit
```

With leave days (use the same ones as during save):

```bash
repafiller -m june --submit -l 5,6,25
```

Preview what would be submitted:

```bash
repafiller -m june --submit --dry-run
```

The submit command fetches existing entries from the server and re-POSTs them with `status: 2`. No `-f` needed — the data is already on the server.

---

## Status reference

| Status | Meaning   |
|--------|-----------|
| 1      | Saved     |
| 2      | Submitted |
| 3      | Declined  |
| 4      | Accepted  |

---

## Notes

- Weekends are always skipped automatically
- If a subject runs out of descriptions in `inventory.txt`, a warning is printed and a random one from the same subject is reused
- Running save on an already filled day overwrites it (server behaviour)
- Running submit on a day with no saved entry skips it with a warning