"""BANK-UI: every piece of English text the bank window can show has a Swedish entry in client/sv-data.js.

Reads the strings the way scripts/build_swedish.py harvests them (quoted and template strings in client/bank.js, the
text and labels of the bank window in client/index.html, and the bank warning of the character list in
client/account.js) and fails on any that sv-data.js can neither match exactly nor through a template.

Run: python3 tests/bank-ui-strings.py
"""
import html.parser
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
data = (ROOT / 'client/sv-data.js').read_text()
text = json.loads(re.search(r'window\.SV_TEXT = (.*);\nwindow\.SV_TEMPLATES', data, re.S)[1])
templates = dict(json.loads(re.search(r'window\.SV_TEMPLATES = (.*);\nwindow\.SV_PHRASES', data, re.S)[1]))
# What the window shows that is not translated on purpose: the key hint is a symbol and a number, and a name is a name.
SKIP = {'Shift-click'}
# Names and loanwords the player sees unchanged, and script text that is not shown, are listed in these hand-written files.
SKIP |= set(json.loads((ROOT / 'scripts/sv-keep.txt').read_text())) | set(json.loads((ROOT / 'scripts/sv-ignore.txt').read_text()))
# What the page's own script turns into text: a number and the word gold (locale.js), and the two places a stack can be,
# which only ever appear after a number and are translated as the templates "{0} in the bank" and "{0} in your bags".
COMPOSED = {'{0} gold': 'locale.js', 'Your purse: {0} gold': 'locale.js', 'in the bank': '{0} in the bank', 'in your bags': '{0} in your bags'}
# Words that are not text: element ids, message types, selectors and class lists in the script.
CODE = re.compile(r'^[a-z][a-z0-9_.\-]*$|^[#.\[)]|^application/|^(Enter|Escape|Tab)$|\(')
classes = lambda value: '-' in value and all(re.fullmatch(r'[a-z][a-z0-9-]*', word) for word in value.split())

def plain_strings(source):
    for match in re.finditer(r"(?<![\\\w])(['\"])([^'\"\n]{3,180})\1", source):
        value = match[2]
        if re.search(r'[A-Za-z]{3}', value) and not re.search(r'[<>{}=\\/;+$]', value) and not CODE.search(value) and not classes(value):
            yield value

def template_strings(source):
    for value in re.findall(r'`([^`\n]{4,260})`', source):
        if re.search(r'[A-Za-z]{3}', value) and not re.search(r'[<>=;/\\]', value) and '${' in value:
            index = iter(range(20))
            yield re.sub(r'\$\{[^{}]*\}', lambda _: '{' + str(next(index)) + '}', value)

class Page(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.inside, self.depth, self.found = False, 0, []
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get('id') == 'bank-panel':
            self.inside = True
        if self.inside:
            if tag in ('div', 'section', 'header', 'footer'):
                self.depth += 1
            for key in ('title', 'placeholder', 'aria-label'):
                if attrs.get(key):
                    self.found.append(attrs[key])
    def handle_endtag(self, tag):
        if self.inside and tag in ('div', 'section', 'header', 'footer'):
            self.depth -= 1
            if self.depth == 0:
                self.inside = False
    def handle_data(self, data):
        if self.inside and data.strip() and re.search(r'[A-Za-z]{3}', data):
            self.found.append(data.strip())

def main():
    page = Page()
    page.feed((ROOT / 'client/index.html').read_text())
    bank = (ROOT / 'client/bank.js').read_text()
    account = (ROOT / 'client/account.js').read_text()
    wanted = {
        *page.found, *plain_strings(bank), *template_strings(bank),
        *(t for t in template_strings(account) if 'bank' in t),
    }
    # Templates are matched as written: a window string that is a template must exist as the same template.
    for part, template in COMPOSED.items():
        if part in wanted and template != 'locale.js':
            assert template in templates, f'"{part}" is shown after a number, so "{template}" needs a Swedish template'
    missing = sorted(v for v in wanted if v not in text and v not in templates and v not in SKIP and v not in COMPOSED)
    assert len(wanted) >= 30, f'harvested only {len(wanted)} strings: the harvest is broken'
    assert not missing, 'No Swedish entry for:\n  ' + '\n  '.join(missing)
    print(f'Bank window: {len(wanted)} strings, all with Swedish text')

if __name__ == '__main__':
    main()
