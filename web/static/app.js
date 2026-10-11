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
