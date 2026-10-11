// Progressive enhancement: without JS every chip is shown.
(function () {
  var buttons = document.querySelectorAll('.kind-filter button');
  if (!buttons.length) return;
  buttons.forEach(function (b) { b.hidden = false; });
  function setKind(kind) {
    if (kind === 'all') { delete document.body.dataset.kind; } else { document.body.dataset.kind = kind; }
    buttons.forEach(function (b) {
      var on = b.dataset.kind === kind;
      b.classList.toggle('active', on);
      b.setAttribute('aria-pressed', on ? 'true' : 'false');
    });
  }
  setKind('all');
  buttons.forEach(function (b) {
    b.addEventListener('click', function () { setKind(b.dataset.kind); });
  });
})();

// Copy buttons (scholars page): hidden without JS, since the text is selectable anyway.
(function () {
  document.querySelectorAll('.copy-btn').forEach(function (b) {
    if (!navigator.clipboard) return;
    b.hidden = false;
    b.addEventListener('click', function () {
      var src = document.getElementById(b.dataset.copy);
      if (!src) return;
      navigator.clipboard.writeText(src.textContent).then(function () {
        var old = b.textContent; b.textContent = b.dataset.done;
        setTimeout(function () { b.textContent = old; }, 1500);
      }).catch(function () {});
    });
  });
})();

// Hebrew font picker: hidden without JS; the choice lives in localStorage (a per-reader convenience).
(function () {
  var sel = document.getElementById('hebfont');
  if (!sel) return;
  sel.parentElement.hidden = false;
  sel.value = document.documentElement.dataset.hebfont || 'frank';
  sel.addEventListener('change', function () {
    var v = sel.value;
    if (v === 'frank') { delete document.documentElement.dataset.hebfont; } else { document.documentElement.dataset.hebfont = v; }
    try { localStorage.setItem('hebfont', v); } catch (e) {}
  });
})();
