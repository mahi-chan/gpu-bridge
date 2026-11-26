# gpu-bridge

An [MCP](https://modelcontextprotocol.io) server that lets an AI coding assistant run
machine-learning work on remote GPUs: Kaggle, Google Colab and Hugging Face.

The server runs on your computer. The assistant calls its tools to get a GPU machine,
start training in the background, follow the logs and metrics, look at plots, and copy
the results back before the machine is recycled.

```
 AI client  ───────►  gpu-bridge  ───────►  Kaggle GPU      free, started for you
 (Cursor, Copilot,  (your computer)       Colab GPU       free, one pasted line
  Gemini…)                             Hugging Face    paid, billed per minute
```

Requirements: macOS, Linux or Windows, and an MCP-capable AI client. The installer
fetches everything else, including Python (through [uv](https://docs.astral.sh/uv/)).

## Contents

- [Install](#install)
- [Choose where the work runs](#choose-where-the-work-runs)
- [Using it](#using-it)
- [Training scripts](#training-scripts)
- [Tools](#tools)
- [Command line](#command-line)
- [Configuration](#configuration)
- [Costs](#costs)
- [Security and privacy](#security-and-privacy)
- [Troubleshooting](#troubleshooting)
- [Development](#development)
- [License](#license)

## Install

Linux and macOS:

```bash
curl -fsSL https://raw.githubusercontent.com/mahi-chan/gpu-bridge/main/install.sh | sh
```

(`wget -qO- <same address> | sh` works if `curl` is missing.)

Windows, in PowerShell:

```powershell
irm https://raw.githubusercontent.com/mahi-chan/gpu-bridge/main/install.ps1 | iex
```

Inside WSL use the Linux command; it registers AI clients installed inside WSL. For
Windows apps such as Cursor on Windows, run the PowerShell command instead.

The installer:

1. downloads gpu-bridge to `~/.gpu-bridge/app` (installing `uv` first if needed),
2. creates an isolated Python environment from the locked dependencies,
3. registers the server with every supported AI client it finds,
4. adds a `gpu-bridge` command to your `PATH`.

Run the same command again to update. Restart your AI client afterwards.

### Supported AI clients

Claude Code, Claude Desktop, Cursor, VS Code (GitHub Copilot), Windsurf, Cline, Gemini
CLI and Codex CLI. For any other client that can launch a local MCP server,
`gpu-bridge install --print` prints the entry to paste into its settings.

## Choose where the work runs

You need one of these. Each has a one-time setup; after that the assistant does the rest.
[docs/CONNECTING.md](docs/CONNECTING.md) has the full walkthrough.

| | Cost | One-time setup | Starting a session |
|---|---|---|---|
| Kaggle | Free, about 30 GPU-hours a week | `gpu-bridge login kaggle` | Automatic |
| Google Colab | Free | None | You run one pasted line in a Colab cell |
| Hugging Face | Paid per minute | `gpu-bridge login huggingface` | Automatic |

Colab needs the pasted line because Google offers no API for starting a session. Kaggle
and Hugging Face do, so gpu-bridge starts those itself.

`gpu-bridge doctor` reports what is ready and what is still missing.

## Using it

Ask the assistant in plain language. Some examples:

| Request | What happens |
|---|---|
| "Connect a Kaggle GPU." | Starts a Kaggle session and attaches to it. |
| "Join the Titanic competition, train a baseline and submit it." | Attaches the data, trains in the background, submits, reports the score. |
| "Train PPO on CartPole with seeds 0, 1 and 2 and plot the rewards." | Three background runs, then reward curves. |
| "Fine-tune SmolLM2 with LoRA on a T4 for at most an hour." | Rents one Hugging Face machine for the job; it stops when training ends. |
| "How is the run going?" | Status, latest metrics and the end of the log. |
| "Save the checkpoints." | Downloads them, or pushes them to a private Hugging Face repo. |
| "Stop everything." | Ends the session and anything still billing. |

Behaviour worth knowing:

- Long runs execute in the background on the remote machine, so they survive chat
  timeouts and dropped connections. A new chat can re-attach to them.
- The same training script and the same status, log, metric and plot tools work on all
  three platforms.
- Remote disks are temporary. Save checkpoints as you go, to your computer or to a
  private Hugging Face repo.

## Training scripts

Any Python script can be launched as a run. Four names are available inside it without
importing anything:

| Name | Purpose |
|---|---|
| `log_metric(step, **values)` | Records numbers for the status, metrics and plot tools. |
| `save_checkpoint_file(path)` | Keeps a file or folder as a checkpoint. |
| `GPU_BRIDGE_RUN_DIR` | The run's working folder. |
| `SEED` | The run's seed, set by seed sweeps. |

Examples:

- [examples/llm_lora_finetune.py](examples/llm_lora_finetune.py): LoRA fine-tune of a language model
- [examples/rl_cartpole.py](examples/rl_cartpole.py): PPO on CartPole
- [examples/cv_mnist.py](examples/cv_mnist.py): a small CNN on MNIST

The assistant can also fetch them with the `example_script` tool.

## Tools

The server exposes 58 tools.

| Group | Tools |
|---|---|
| Get a machine | `kaggle_runtime_start`, `colab_runtime_start`, `connect_runtime`, `runtime_stop`, `runtime_status` |
| Hugging Face machines | `hf_hardware`, `hf_job_launch`, `hf_job_list`, `hf_job_cancel`, `hf_runtime_start`, `hf_runtime_connect`, `hf_runtime_stop` |
| Run code and files | `run_code`, `upload_file`, `download_file`, `fetch_image` |
| Training runs | `launch_training`, `get_run_status`, `get_logs`, `get_metrics`, `plot_metrics`, `stop_run`, `list_runs`, `save_checkpoint`, `restore_checkpoint` |
| Colab notebook in your browser | `colab_ui_connect`, `colab_ui_call` |
| Colab API (create runtimes from code) | `colab_api_tools`, `colab_api_call` |
| Notebooks | `notebook_create`, `notebook_read`, `notebook_add_cell`, `notebook_edit_cell`, `notebook_delete_cell`, `notebook_run_cell` |
| Reinforcement learning | `rl_setup`, `rl_reward_curve`, `rl_record_rollout`, `rl_seed_sweep` |
| Computer vision | `cv_load_dataset`, `cv_training_curves`, `cv_show_predictions` |
| Kaggle competitions | `kaggle_search_datasets`, `kaggle_competition_files`, `kaggle_submit`, `kaggle_submissions`, `kaggle_leaderboard` |
| Hugging Face Hub and Spaces | `hf_whoami`, `hf_search`, `hf_upload`, `hf_download`, `hf_push_run`, `hf_space_status`, `hf_space_hardware`, `hf_space_pause`, `hf_space_restart` |
| Help | `setup_guide`, `example_script` |

## Command line

```
gpu-bridge doctor               show what is set up and the next step for anything missing
gpu-bridge login kaggle         log in to Kaggle (once)
gpu-bridge login huggingface    log in to Hugging Face (once)
gpu-bridge clients              list supported AI clients and where they were found
gpu-bridge install              register with AI clients (--client NAME, repeatable; --print)
gpu-bridge uninstall            remove it from them
gpu-bridge serve --http         serve over local HTTP, for clients that connect by URL
```

`gpu-bridge serve` without options runs the server over stdio, which is what the
registered clients use. With `--http` it listens on `http://127.0.0.1:8765/mcp`.

## Configuration

| Variable | Effect |
|---|---|
| `GPU_BRIDGE_RENDEZVOUS_URL` | Relay used by new sessions to announce themselves. Defaults to [ntfy.sh](https://ntfy.sh); point it at your own ntfy server if you prefer. Set it in the AI client's environment. |
| `GPU_BRIDGE_DIR` | Installer only: where the app is installed. Default `~/.gpu-bridge/app`. |
| `GPU_BRIDGE_BIN` | Installer only: where the `gpu-bridge` command is placed. Default `~/.local/bin`. |
| `GPU_BRIDGE_BRANCH` | Installer only: branch to install. Default `main`. |

Kaggle and Hugging Face credentials are not configured here. They stay with the official
tools: `~/.kaggle/kaggle.json` and the Hugging Face token store.

## Costs

- Kaggle and Colab are free. A Kaggle session started by gpu-bridge ends on request,
  after 30 idle minutes, or at its time limit (6 hours by default), so it does not use
  up your weekly GPU quota.
- Hugging Face bills per minute until a machine ends. Every machine gets a time limit,
  the interactive one shuts itself down after 30 idle minutes, and `hf_job_list` shows
  anything still running. `hf_hardware` shows current prices.

## Security and privacy

- Logins stay with the official Kaggle and Hugging Face tools on your computer.
  gpu-bridge does not write tokens into an AI client's configuration.
- Kaggle and Colab sessions are reached through a temporary public tunnel protected by a
  random one-time code known only to your computer and that session.
- To find a new session without manual copying, the session posts its tunnel address to a
  relay. Only the address is sent, signed with the one-time code so it cannot be
  swapped; the code itself never goes through the relay.
- When a tool needs your Hugging Face or Kaggle login on the remote machine (pushing
  checkpoints, downloading competition data), the credential is lent for that single
  command and not stored.
- `gpu-bridge serve --http` has no password. Keep it on localhost; anyone who can reach
  it can rent machines on your Hugging Face account.

## Troubleshooting

| Symptom | What to do |
|---|---|
| The assistant has no gpu-bridge tools | Restart the AI client and check `gpu-bridge clients`. |
| "No Kaggle login found" | Run `gpu-bridge login kaggle`. |
| A Kaggle session "ended before connecting" | Verify your phone number on kaggle.com (required for GPU and internet), or check that the weekly GPU quota is not used up. |
| "Not connected yet" on Colab | Check that the pasted cell is still running and has printed `connected`. |
| "No Hugging Face token found" | Run `gpu-bridge login huggingface`. |
| Hugging Face error 402 | Add credits or a payment method at huggingface.co/settings/billing. |
| A run disappeared | The machine was recycled. Save checkpoints as you go. |

## Development

```bash
git clone https://github.com/mahi-chan/gpu-bridge.git
cd gpu-bridge
uv sync
uv run pytest
uvx ruff check src tests
./install.sh        # register this checkout with your AI clients
```

The tests cover the installers, every tool against a local Jupyter server, and the Kaggle
and Hugging Face calls against stubs. Sessions on the live services depend on your
accounts and are not covered; please open an issue with the message you saw if something
misbehaves there.

```
src/gpu_bridge/
  cli.py, installer.py     the gpu-bridge command and the client installer
  server.py                registers every tool group
  tools/                   the tools, one module per group
  connectors/              Jupyter, Kaggle, Hugging Face, pairing, local state
  remote/entrypoint.py     the program that runs on the remote machine
examples/                  training scripts
docs/CONNECTING.md         connecting each platform, step by step
tests/                     test suite
```

## License

MIT, see [LICENSE](LICENSE).
