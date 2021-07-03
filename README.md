# SimpleFuzzy package for Sublime Text

Jump to everywhere by built-in fuzzy function to perform a line-based searching for the current file or the active project folder. If you open up multiple folders in the same sublime window, the folder relative to the current open file will be used for project searching.

## Usage

Example key bindings to the window commands:

```json
[
	{ "keys": ["super+k", "super+f"], "command": "fuzzy_current_file"},
	{ "keys": ["super+k", "super+p"], "command": "fuzzy_active_project"},
]
```

Or, simply run the following commands by `Ctrl-Shift-P` in command palette:

- `SimpleFuzzy: Current File…`
- `SimpleFuzzy: Active Project…`

## Customization

Your favorite file listing command can be specified by adding user setting.

```json
{
	"simple_fuzzy_ls_cmd": "ag foo {folder}"
}
```

Variable `{folder}` is the target folder to be searched. In such example, `which ag` will be used to check if the command exists.

If user-defined command fails or not specified, default using the following commands for fallback:
1. `rg`: `rg --files "{folder}"` (highly recommended, required [ripgrep](https://github.com/BurntSushi/ripgrep))
2. `git`: `git -C "{folder}" ls-files`
3. `built-in`: Python built-in `os.walk` function

User can also specify the prefer one as: `rg`, `git`, or `built-in`

## Debugging

Run the following command in Console view to toggle console log.

```python
>>> window.run_command('simple_fuzzy_debug_toggle')
```

## Known issues

- Performance issue
- Always go to the line begining
