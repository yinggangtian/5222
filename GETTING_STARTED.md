# 🐷 Getting Started with Piglet

This guide takes you from a fresh computer to Assignment 1 running on your screen, with trains moving
in a window. It assumes no prior experience with terminals, Git or Python environments; if you have
used them before, skip ahead.

Work through the steps in sequence. The whole thing takes about 20 minutes, most of which is waiting
for downloads.

- [Step 0: Open a terminal](#step-0-open-a-terminal)
- [Step 1: Install Git](#step-1-install-git)
- [Step 2: Install uv](#step-2-install-uv)
- [Step 3: Download your assignment repository](#step-3-download-your-assignment-repository)
- [Step 4: Check it works](#step-4-check-it-works)
- [Step 5: Watch it run](#step-5-watch-it-run)
- [Step 6: Start the assignment](#step-6-start-the-assignment)
- [The piglet search library](#the-piglet-search-library)
- [Where to go next](#where-to-go-next)
- [Troubleshooting](#troubleshooting)

The assignment is tested with Python 3.14 on modern versions of Windows, macOS and Linux, and inside
WSL (Windows Subsystem for Linux). Pick whichever you already have; the assignment is the same on
each.

> **What am I installing?** Just two things: Git, to download code, and uv, to manage Python. The
> right Python interpreter, Piglet, and the Flatland railway simulator all install themselves the
> first time you run the assignment in [Step 4](#step-4-check-it-works). You never install Python
> yourself.

---

Step 0: Open a terminal
---

A **terminal** is a window where you type commands instead of clicking buttons. Nearly everything
below happens in one. Open it now and leave it open.

### Windows

Press <kbd>Win</kbd> + <kbd>X</kbd> and choose **Terminal** (on older machines: **Windows
PowerShell**). You can also press <kbd>Win</kbd>, type `terminal`, and press <kbd>Enter</kbd>.

You should see a prompt ending in `>`, something like:

```
PS C:\Users\you>
```

That is PowerShell, and it is what the Windows commands in this guide assume.

### WSL on Windows

WSL runs a real Ubuntu Linux system inside Windows. It is a good choice if your unit or your own
projects expect Linux tools, and the assignment runs on it, graphical window included.

If you do not have WSL yet, open **Terminal as Administrator** (press <kbd>Win</kbd>, type
`terminal`, then right-click it and choose **Run as administrator**) and run:

```console
> wsl --install
```

Restart your computer when it asks. On the next boot an Ubuntu window opens and asks you to invent a
username and password. The password is for Ubuntu, and you will not see the characters as you type
them.

From then on, open WSL by pressing <kbd>Win</kbd>, typing `ubuntu`, and pressing <kbd>Enter</kbd>.
Your prompt ends in `$`:

```
you@machine:~$
```

Once you are at that `$` prompt you are on Linux. From here on, follow the Linux instructions rather
than the Windows ones.

### macOS

Press <kbd>Cmd</kbd> + <kbd>Space</kbd>, type `terminal`, press <kbd>Enter</kbd>. Your prompt ends in
`%` or `$`.

### Linux

Press <kbd>Ctrl</kbd> + <kbd>Alt</kbd> + <kbd>T</kbd>, or find **Terminal** in your applications
menu. Your prompt ends in `$`.

### How to read the commands in this guide

Code blocks show a prompt character that you do not type. Type only what comes after it.

```console
$ echo hello
hello
```

Here you type `echo hello` and press <kbd>Enter</kbd>; `hello` is the computer's reply. `$` marks a
macOS/Linux/WSL prompt and `>` marks a Windows PowerShell prompt.

---

Step 1: Install Git
---

**Git** is the tool that downloads your assignment repository and tracks changes to your own work as
you go.

First, check whether you already have it:

```console
$ git --version
```

If that prints a version number (`git version 2.43.0` or similar), skip to
[Step 2](#step-2-install-uv). If it says *command not found* or *not recognized*, install it:

| Platform | Command |
| --- | --- |
| Windows | `winget install --id Git.Git -e` |
| WSL / Ubuntu / Debian | `sudo apt update && sudo apt install git` |
| macOS | `xcode-select --install` |
| Fedora | `sudo dnf install git` |
| Arch | `sudo pacman -S git` |

Notes:

- **Windows**: if `winget` is not recognised, download the installer from
  [git-scm.com](https://git-scm.com/download/win) and accept every default.
- **WSL/Linux**: `sudo` means "run as administrator". It will ask for the password you invented in
  Step 0. Nothing appears on screen as you type it; type it and press <kbd>Enter</kbd> anyway.
- **macOS**: this installs Apple's Command Line Tools, which include Git. A dialog box will pop up;
  click **Install** and wait.

**Close your terminal and open a new one**, then confirm it worked:

```console
$ git --version
git version 2.43.0
```

> **Why a new terminal?** A terminal reads the list of available commands once, when it starts. A
> program installed afterwards is invisible to it until you open a fresh one. If a command you just
> installed is "not found", this is almost always why.

---

Step 2: Install uv
---

**uv** manages Python for you, so do not install Python yourself. uv reads the assignment's
`.python-version` file, downloads the interpreter it names (currently 3.14.6), and keeps it isolated
from the rest of your machine. That isolation matters here, because your code is marked by running
it: the tutor's setup has to match yours.

Run the installer for your platform:

**Windows** (PowerShell):

```console
> powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**macOS, Linux and WSL**:

```console
$ curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Close your terminal and open a new one** (see the note in Step 1), then check:

```console
$ uv --version
uv 0.9.5
```

Any version number means you are fine. If it says *command not found*, see
[Troubleshooting](#uv-command-not-found).

---

Step 3: Download your assignment repository
---

Your unit gives you the URL of your own repository. That is where your marked work lives, so use it
here rather than a classmate's or one copied from this page.

Choose where to keep your work and move there. `cd` means "change directory":

```console
$ cd Documents
```

Now download the code, substituting the URL your unit gave you:

```console
$ git clone <the-url-your-unit-gave-you>
$ cd <the-folder-it-created>
```

Because the repository is private, Git will ask you to authenticate. How depends on your unit: a
browser login, an SSH key, or an access token. Follow your unit's instructions; if you get stuck,
see [Troubleshooting](#git-clone-asks-for-a-password-or-is-rejected).

You are now *inside* the project folder, which is where every remaining command in this guide must be
run. If you close your terminal and come back tomorrow, you will need to `cd` back here first.

Check you are in the right place; you should see `question1.py` and `pyproject.toml`:

```console
$ ls          # Windows PowerShell: dir
```

> **WSL users**: keep your code in the Linux home directory (`~`, where you land by default), not in
> `/mnt/c/...`. Working across the Windows/Linux boundary is dramatically slower.

---

Step 4: Check it works
---

There is no install step. Just run question 1:

```console
$ uv run python question1.py
```

The first time, this sits there for a few minutes. That is `uv run` setting the project up before it
runs anything: it reads `.python-version` and `pyproject.toml`, downloads the right Python, and
installs Piglet, Flatland, and the rest of the dependencies at the versions pinned in `uv.lock`. All
of it goes into `.venv`, a hidden folder holding a virtual environment used only by this project.
Later runs skip the setup and start immediately.

> **Always use `uv run`.** It runs your command inside the project's environment, re-checking that
> environment first. `uv run python question1.py` works; plain `python question1.py` fails with
> `Cannot load flatland modules!`, because that Python does not have Flatland installed. You never
> activate the environment or install into it by hand. This trips people up more than anything else
> in the setup — [Troubleshooting](#cannot-load-flatland-modules) covers it.

The three question files already contain a dummy implementation: a naive planner that always takes
the first available track. It is there so the assignment runs before you have written any code, and
replacing it is the assignment.

Once the setup finishes, it solves 40 test cases in a row and prints a table:

```
Test case          | Total agents | Agents done  | DDLs met     | Plan Time  | SIC          | Makespan     | ...
single_test_case/level0_test_0 | 1            | 0            | 0            | 0.0        | 160          | 16           | ...
single_test_case/level0_test_1 | 1            | 0            | 0            | 0.0        | 160          | 16           | ...
single_test_case/level0_test_2 | 1            | 1            | 1            | 0.0        | 3            | 3            | ...
...
Summary            | 40 (sum)     | 15 (sum)     | 15(sum)      | 0.0(sum)   | 23617 (sum)  | 2737 (sum)   | ...
```

If you see that table, your setup is complete: one row per test case, then a `Summary` row.

The column to watch is `Agents done`: how many trains reached their goal. The dummy gets 15 of 40,
stumbling onto the goal when the track happens to lead there and getting lost otherwise. That is your
starting line; a correct single-agent search should reach 40.

The other columns score *how good* the successful plans are: `SIC` (sum of individual costs, i.e.
total travel time over all trains) and `Makespan` (the time the last train arrives), both
lower-is-better. Your unit's assignment specification defines how these turn into a mark.

At the end you will see:

```
Press enter to exit:
```

The program has finished and is waiting for you; press <kbd>Enter</kbd>. (It waits here so the
visualiser window in the next step stays open until you are done looking at it.)

---

Step 5: Watch it run
---

The table tells you *whether* the trains arrived. To see *why* they did not, watch them.

Open [question1.py](question1.py) in your editor. Near the top are four switches:

```python
debug = False
visualizer = False

test_single_instance = False
level = 0
test = 0
```

Set the visualiser on, and pin the run to a single test case, or you will sit through all 40 of them,
one window at a time:

```python
debug = True
visualizer = True

test_single_instance = True
level = 0
test = 0
```

Run it again:

```console
$ uv run python question1.py
```

A window opens showing a train on a railway, and you can watch it follow the path your `get_path`
returned. Closing the window ends the program. You will also see a panel in the terminal like:

```
╭─ 🚂 FLATLAND ────────────────────────────────────╮
│  Showing the visualisation in a desktop window.  │
│  Closing that window will end this program.      │
│  Also viewable at http://127.0.0.1:8081/         │
╰──────────────────────────────────────────────────╯
```

If no window appears, the simulation is still running; open the `http://127.0.0.1:8081/` address in
your browser to see the same thing. See
[Troubleshooting](#the-window-does-not-open-and-i-get-a-url-instead).

`debug = True` adds running commentary to the terminal, including the message you will come to know
best:

```
Agent 0 cannot reach location (5, 7) from location (3, 2). Path is inconsistent.
```

That means your path jumped between two cells that are not connected by track. Trains cannot teleport
or reverse on the spot, which is what makes the assignment a search problem.

> **Turn the visualiser off before a full run.** Rendering 40 or 56 episodes is slow, and you only
> need the table.

### Changing how the run is displayed

`visualizer = True` uses the default settings. To change them, assign a `VisualiserOptions` instead
of `True`:

```python
visualizer = VisualiserOptions(
    delay=0.3,      # seconds to pause between timesteps; 0 runs at full speed
    headless=False, # True: no window, serve to your browser instead
    wait=True,      # hold the first frame until you are watching
    port=8080,      # serve on a fixed port (headless mode)
    cell_size=40,   # pixels per grid cell
)
```

Every field has a default, so set only the ones you care about. The same block is already at the top
of each question file, commented out, so you can uncomment it instead of typing it.

`delay` is the one you will change most often. Raise it to follow a train cell by cell; drop it to 0
when you only want to see roughly where the plan goes wrong. Use `headless=True` if your machine
cannot open a window: the run is served to your browser straight away, with no window attempt first.
And `wait=True` holds the very first frame until you have the view open, so a short episode does not
finish before you have looked at it.

---

Step 6: Start the assignment
---

There are three questions, one file each. You change only the `get_path` function (and, in question
3, `replan`); leave the code below the `if __name__ == "__main__":` line alone, since that is what
the markers run.

| File | Question | Test cases |
| --- | --- | --- |
| [question1.py](question1.py) | One train, find a shortest path | 40, in `single_test_case/` (levels 0–4) |
| [question2.py](question2.py) | Many trains, plans must not collide | 56, in `multi_test_case/` (levels 0–6) |
| [question3.py](question3.py) | Many trains, some breaking down and needing a replan mid-episode | 56, plus a deadline (`.ddl`) per case |

```console
$ uv run python question1.py    # single-agent path finding
$ uv run python question2.py    # multi-agent, conflict-free
$ uv run python question3.py    # multi-agent with malfunctions and replanning
```

Higher `level` numbers mean bigger maps and more trains, so start at level 0 and work up. Question 2
and 3 take longer to run than question 1, since there is more to simulate.

What each function receives and must return is documented in the comments above it. In short,
`get_path` receives a start, a goal, and `rail`, a Flatland `GridTransitionMap` that says which moves
the track allows; it must return the list of `(x, y)` cells the train visits, one per timestep.

The one call you cannot avoid is:

```python
valid_transitions = rail.get_transitions(x, y, direction)
```

It returns four booleans (can I move north, east, south, west) for the direction the train is already
facing. That direction is the crux of the assignment: a train's legal moves depend on its heading, so
a search state is a *position together with a direction*. Treat it as a plain grid and you will
produce paths the simulator rejects.

To understand the railway model — transitions, agent attributes, malfunctions, and what the simulator
does with the actions you produce — read the [Flatland getting started
guide](https://github.com/ShortestPathLab/flatland/blob/master/GETTING_STARTED.md). It covers
Flatland in depth, and this assignment builds on it.

---

The piglet search library
---

You do not have to write A\* from a blank page. This repository *is* Piglet, a library of search
algorithms and the domains they run on, and you are welcome to lift its pieces into your `get_path`.

A search needs three things: a **domain**, an **expander** that generates a state's successors, and a
**search** that puts them together.

```python
from lib_piglet.domains import gridmap
from lib_piglet.expanders.grid_expander import grid_expander
from lib_piglet.search.graph_search import graph_search
from lib_piglet.search.search_node import compare_node_f
from lib_piglet.utils.data_structure import bin_heap
from lib_piglet.heuristics import gridmap_h

gm = gridmap.gridmap("./example/gridmap/empty-16-16.map")
expander = grid_expander(gm)

search = graph_search(
    bin_heap(compare_node_f),                       # open list, ordered on f
    expander,
    heuristic_function=gridmap_h.piglet_heuristic,
)

solution = search.get_path((1, 2), (10, 2))
print(solution)
```

Note that this is a *gridmap*, where a state is just an `(x, y)` position; the Flatland railway is
not, for the reason given in Step 6. Treat the library as a reference to borrow from rather than a
drop-in answer.

You can also run searches straight from the command line, which is a quick way to see how the
algorithms differ:

```console
$ uv run piglet -p ./example/arena2.min.scen -f graph -s a-star
$ uv run piglet -p ./example/arena2.min.scen -f graph -s uniform    # compare the nodes expanded
$ uv run piglet --help
```

Add `--log trace` to record a search trace, then load it into
[Posthoc](https://posthoc.pathfinding.ai) and step through the search node by node:

```console
$ uv run piglet -p ./example/arena2.min.scen -f graph -s a-star --log trace
```

---

Where to go next
---

- **[Flatland getting started guide](https://github.com/ShortestPathLab/flatland/blob/master/GETTING_STARTED.md)**
  — read this next. It documents Flatland: the environment, the railway model, agent attributes,
  malfunctions and the renderer.
- **[README.md](README.md)** — the Piglet library and its command line, in more detail.
- **Your unit's assignment specification** — the definitive word on what to implement and how it is
  marked. This guide only gets you to the starting line.

---

Troubleshooting
---

### `uv`: command not found

You almost certainly need to open a new terminal — see the note at the end of
[Step 1](#step-1-install-git). If a fresh terminal still cannot find it, the installer put `uv`
somewhere your terminal does not look. Fix it for the current terminal with:

**macOS / Linux / WSL:**

```console
$ export PATH="$HOME/.local/bin:$PATH"
```

**Windows:**

```console
> $env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
```

That lasts until you close the terminal. To make it permanent, restart your machine and run
`uv --version` in a new terminal; if it still fails, ask on the unit forum rather than fighting it.

### `git clone` asks for a password, or is rejected

Your assignment repository is private, so a prompt to authenticate is expected; the only question is
which method your unit uses (browser login, SSH key, or access token). Follow your unit's
instructions, and note that your normal account password often will not work, since many hosts
require a token or key instead.

If you are refused access outright, check the URL for a typo before anything else, and confirm you
are using your own repository's URL.

### `Cannot load flatland modules!`

Two causes, in order of likelihood:

1. **You ran `python question1.py` instead of `uv run python question1.py`.** Every command in this
   project starts with `uv run`. Without it you get whatever Python happens to be on your machine,
   which does not have Flatland installed.
2. **You are in the wrong folder.** Commands must run from the project folder — the one containing
   `pyproject.toml`. Check where you are with `pwd` (macOS/Linux/WSL) or `Get-Location` (Windows),
   and `cd` back if needed.

If neither fixes it, run `uv sync` — that does the install on its own, without running anything
afterwards, so any error it hits is printed plainly instead of scrolling past.

### The window does not open, and I get a URL instead

If Flatland cannot open a desktop window, it serves the same simulation to your browser and prints
the address instead. Open it (usually `http://127.0.0.1:8081/`) to see the same trains. The window is
the only thing missing.

On a Linux desktop the window needs GTK/WebKit system libraries that pip cannot install:

```console
$ sudo apt install libgirepository1.0-dev gir1.2-webkit2-4.1 python3-gi
$ uv sync --reinstall
```

The [Flatland guide's troubleshooting
section](https://github.com/ShortestPathLab/flatland/blob/master/GETTING_STARTED.md#troubleshooting)
goes into more depth, including WSL.

### The terminal is stuck at `Press enter to exit:`

The run has finished; it holds here so the visualiser window stays open while you look at it. Press
<kbd>Enter</kbd> to exit. Your results are in the table printed just above.

### Everything runs, but almost no agents are done

That is the dummy implementation, which is meant to do badly — see
[Step 4](#step-4-check-it-works). 15 of 40 on question 1 means your setup is correct and you have not
started yet. Start writing `get_path`.

### A run takes forever

Question 2 and 3 simulate 56 multi-agent episodes, and a planner that never reaches the goal keeps
going until the timestep limit, which is the slowest possible case. While developing, pin yourself to
one instance:

```python
test_single_instance = True
level = 0
test = 0
```

Also make sure `visualizer = False` for full runs — rendering every episode is far slower than
running it.

### Something else

Ask on the unit forum. Include your operating system, the command you ran, and the complete error
message; screenshots of a single line are rarely enough to diagnose anything.
