// Children are always added as text nodes, never as HTML, so player-supplied names can't inject markup.
export function h(tag, props, ...children) {
  const el = document.createElement(tag);
  for (const [key, value] of Object.entries(props || {})) {
    if (value == null || value === false) continue;
    if (key === 'class') el.className = value;
    else if (key === 'style') setStyle(el, value);
    else if (key.startsWith('on')) el.addEventListener(key.slice(2), value);
    else if (key in el) el[key] = value;
    else el.setAttribute(key, value === true ? '' : value);
  }
  return add(el, children);
}

/* Append children, flattening arrays and skipping null/false. Unlike el.append(), which would print them. */
export function add(el, ...children) {
  for (const child of children.flat(Infinity)) {
    if (child == null || child === false) continue;
    el.append(child.nodeType ? child : document.createTextNode(String(child)));
  }
  return el;
}

function setStyle(el, style) {
  for (const [name, value] of Object.entries(style)) {
    if (name.startsWith('--')) el.style.setProperty(name, value);
    else el.style[name] = value;
  }
}

export function clear(el) {
  el.replaceChildren();
  return el;
}

export function credits(amount) {
  return `${amount.toLocaleString('en-US')} cr`;
}

export function signedCredits(amount) {
  return `${amount > 0 ? '+' : ''}${credits(amount)}`;
}

export function netClass(amount, even = 'push') {
  return amount > 0 ? 'win' : amount < 0 ? 'lose' : even;
}

export function limits(table) {
  const top = table.max_bet ? credits(table.max_bet) : 'no limit';
  return `${credits(table.min_bet)} to ${top}`;
}
