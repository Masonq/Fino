"""
Проверка всех экранов: хуки (useState/useEffect/useRef/useCallback/useMemo/useFocusEffect/use*) не должны стоять ниже
раннего выхода (`if (...) return` в теле компонента) — иначе при смене условия меняется число хуков и экран падает
(React #310). Запуск: python3 tools-check-hooks.py — печатает нарушения, код выхода 1 если есть.
"""
import glob, re, sys

bad = []
for f in glob.glob('app/**/*.tsx', recursive=True) + glob.glob('src/**/*.tsx', recursive=True):
    src = open(f, encoding='utf-8').read()
    # компоненты: function Name(...) { ... } на верхнем уровне — тело до следующей функции верхнего уровня
    for m in re.finditer(r'^(?:export default )?function ([A-Z]\w*)\([^\n]*\{\s*$', src, re.M):
        start = m.end()
        nxt = re.search(r'^(?:export default |export )?(?:function |const [A-Z_]+ = )', src[start:], re.M)
        body = src[start:start + nxt.start()] if nxt else src[start:]
        lines = body.split('\n')
        first_ret = None
        for i, l in enumerate(lines):
            # ранний выход на уровне тела компонента (2 пробела): `  if (...) return ...` или `  if (...) {` с return внутри
            if re.match(r'^  if \(', l):
                block = l if l.rstrip().endswith(')') or 'return' in l else '\n'.join(lines[i:i + 40])
                if 'return' in (l if 'return' in l else block.split('\n  }')[0]):
                    first_ret = i
                    break
            if re.match(r'^  return[ (]', l):
                break
        if first_ret is None:
            continue
        for l in lines[first_ret + 1:]:
            if re.match(r'^  return[ (]', l):
                break
            if re.search(r'^\s{2}(?:const|let) [^=]*= use[A-Z]\w*(?:<[^\n]*?>)?\(|^\s{2}use[A-Z]\w*(?:<[^\n]*?>)?\(', l):
                bad.append(f'{f}: {m.group(1)}: хук ниже раннего выхода — {l.strip()[:80]}')
print('\n'.join(bad) if bad else 'нарушений нет')
sys.exit(1 if bad else 0)
