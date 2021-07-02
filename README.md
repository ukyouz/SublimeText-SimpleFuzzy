# SimpleFuzzy package for Sublime Text

Use built-in fuzzy function to perform fuzzy search for current file and project.

If you open up multiple folders in the same sublime window, the folder relative to the current open file will be used for project searching.

## Usage

Add key binding to the following commands:

- `fuzzy_line`
- `fuzzy_project_line`

Or, simply run the following commands by `Ctrl-Shift-P` in command palette:

- `Fuzzy Line`
- `Fuzzy Project Line`

## Costomization

Your favorite file listing command can be specified by user settings.

```json
{
	"simple_fuzzy_ls_cmd": "ag foo {folder}"
}
```

Variable `{folder}` is the target folder to be searched. In such example, `which ag` will be used to check if the command exists.

If user-defined command fails or not specified, default using the following commands for fallback:
1. `rg`: `rg --files "{folder}"`
2. `git`: `git -C "{folder}" ls-files`
3. `built-in`: Python built-in `os.walk` function

User can also specify the prefer one as: `rg`, `git`, or `built-in`

## Debugging

Run the following command in ccommand palette to toggle console log.
```python
>>> window.run_command('simple_fuzzy_debug_toggle')
fuzzy project in: /path/to/project with Encoding=UTF-8
git -C "/path/to/project" status
git -C "/path/to/project" ls-files
```

## Known issues

- Performance issue
- Always go to the line begining
