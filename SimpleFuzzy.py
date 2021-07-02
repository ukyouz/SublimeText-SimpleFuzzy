import sublime
import sublime_plugin
import threading
import os
import re
import subprocess

class EditorLineInputHandler(sublime_plugin.ListInputHandler):
    def name(self):
        return "pos"

    def placeholder(self):
        return "Search content line..."

    def list_items(self):
        window = sublime.active_window()
        view = window.active_view()
        regions = view.find_all('.+\n')
        lines = [view.substr(region).strip().replace('\t', '') for region in regions]
        positions = [r.begin() for r in regions]
        return [
            sublime.ListInputItem(
                text=line_str,
                value=pos,
            ) for pos, line_str in zip(positions, lines)
            if re.match('\s*\d+$', line_str) is None and len(line_str)
        ]

class FuzzyLineCommand(sublime_plugin.WindowCommand):
    def run(self, pos):
        self.window.active_view().sel().clear()
        self.window.active_view().sel().add(sublime.Region(pos))
        self.window.active_view().show_at_center(sublime.Region(pos))

    def input(self, args):
        if "pos" not in args:
            return EditorLineInputHandler()
        else:
            return None

class GrepFileLinesThread(threading.Thread):
    def __init__(self, folder, filename, encoding='UTF-8', timeout=30):
        self.folder = folder
        self.filename = filename
        self.encoding = encoding
        self.rel_filename = self.filename.replace(folder, '')
        self.timeout = timeout
        self.result = None
        threading.Thread.__init__(self)

    def run(self):
        self.result = self._read_filelines(self.filename)

    def _read_filelines(self, filename):
        with open(self.filename, 'r', encoding=self.encoding) as fs:
            try:
                lines = [
                    l.strip().replace('\t', '')
                    for l in fs.readlines()
                ]
                return [
                    sublime.ListInputItem(
                        text=line_str,
                        value=(self.filename, line_no + 1),
                        annotation='%s:%s'%(self.rel_filename, line_no+1),
                    ) for line_no, line_str in enumerate(lines)
                    if len(line_str) > 0
                ]
            except UnicodeDecodeError:
                return []

class FolderLineInputHandler(sublime_plugin.ListInputHandler):
    def __init__(self, window):
        self.window = window
        self.view = self.window.active_view()

    def name(self):
        return "file_lines"

    def placeholder(self):
        return "Search content line..."

    def list_items(self):
        folders = self.window.folders()
        if len(folders) == 0:
            sublime.error_message('No project folder found for Fuzzy Project Line search.')
            return []
        active_folder = next(
            (f for f in folders if f in (self.view.file_name() or '')),
            folders[0]
        )
        print('fuzzy project in: %s with Encoding=%s'%(active_folder, encoding))
        encoding = self.view.encoding() if self.view.encoding() != 'Undefined' else 'UTF-8'
        file_list = self._list_files(active_folder, encoding)
        threads = []
        lines = []
        for file in file_list:
            if not os.path.exists(file):
                continue
            view = self.window.find_open_file(file)
            if view == None:
                thread = GrepFileLinesThread(active_folder, file, encoding)
                thread.start()
                threads.append(thread)
            else:
                lines += self._grep_view_lines(active_folder, view)

        for thread in threads:
            thread.join()
            lines += thread.result

        return lines

    # return filenames including folder name
    def _list_files(self, folder, encoding='UTF-8'):
        user_pref_cmd = self.view.settings().get('simple_fuzzy_ls_cmd', '')
        user_pref_chk = user_pref_cmd.split()[0] if len(user_pref_cmd) else ''

        def _fmt_cmd(fmt):
            return '{_fmt}'.format(_fmt=fmt).format(folder=folder)

        def _ls_dir(check_cmd, ls_cmd):
        OK = 0
            if os.system(_fmt_cmd(check_cmd)) != OK:
                return []
            f_list = subprocess.check_output(_fmt_cmd(ls_cmd), shell=True).splitlines()
            return [f.decode(encoding) for f in f_list]

        def _builtin_ls():
            # default fallback for listing files in folder
            f_list = []
            for root, dirs, files in os.walk(folder):
                f_list += [os.path.join(root, f) for f in files]
            return f_list

        default_cmds = {
            'rg': lambda: _ls_dir('which rg', 'rg --files "{folder}"'),
            'git': lambda: _ls_dir('git -C "{folder}" status', 'git -C "{folder}" ls-files'),
            'built-in': _builtin_ls,
        }

        file_list = []
        if user_pref_cmd in default_cmds:
            file_list = default_cmds[user_pref_cmd]()
        else:
            chk_cmd = 'which %s' % user_pref_chk
            ls_cmd = user_pref_cmd
            file_list = _ls_dir(chk_cmd, ls_cmd)
        
        if len(file_list) == 0:
            for cmd in ('rg', 'git'):
                file_list = default_cmds[cmd]()
                if len(file_list):
                     break
        if len(file_list) == 0:
            file_list = _builtin_ls()
        if len(file_list) and not os.path.exists(file_list[0]):
            # relative -> fullpath
            file_list = [os.path.join(folder, f) for f in file_list]

        return [f for f in file_list if os.path.isfile(f)]

    def _grep_view_lines(self, folder, view):
        filename = view.file_name()
        rel_filename = filename.replace(folder, '')
        regions = view.find_all('.*\n')
        lines = [
            (line_no + 1, view.substr(region).strip().replace('\t', ''))
            for line_no, region in enumerate(regions)
        ]
        return [
            sublime.ListInputItem(
                text=line_str,
                value=(filename, line_no),
                annotation='%s:%s'%(rel_filename, line_no),
            ) for line_no, line_str in lines
            if len(line_str.strip()) > 0
        ]

class FuzzyProjectLineCommand(sublime_plugin.WindowCommand):
    def run(self, file_lines):
        file = file_lines[0]
        line = file_lines[1]
        view = self.window.open_file(file)
        self._go_to_file_line(view, line)

    def _go_to_file_line(self, view, line):
        if view.is_loading():
            sublime.set_timeout_async(
                lambda: self._go_to_file_line(view, line),
                50
            )
            return
        # Convert from 1 based to a 0 based line number
        line = int(line) - 1

        # Negative line numbers count from the end of the buffer
        if line < 0:
            lines, _ = view.rowcol(view.size())
            line = lines + line + 1

        pt = view.text_point(line, 0)

        view.sel().clear()
        view.sel().add(sublime.Region(pt))

        view.show_at_center(pt)
        
    def input(self, args):
        if "file_lines" not in args:
            return FolderLineInputHandler(self.window)
        else:
            return None



