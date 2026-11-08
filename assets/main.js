// Country search (home + hub pages) and country filter (countries page)
(function () {
  var input = document.getElementById('cq');
  if (input) {
    var go = function () {
      var v = input.value.trim().toLowerCase();
      if (!v) { input.focus(); return; }
      var opts = document.querySelectorAll('#clist option'), slug = null;
      for (var i = 0; i < opts.length; i++) {
        var n = opts[i].value.toLowerCase();
        if (n === v) { slug = opts[i].dataset.slug; break; }
        if (!slug && n.indexOf(v) === 0) slug = opts[i].dataset.slug;
      }
      if (!slug) { input.setCustomValidity('Please pick a country from the list'); input.reportValidity(); setTimeout(function(){input.setCustomValidity('')},2000); return; }
      var kind = document.getElementById('ckind').value;
      window.location.href = (input.dataset.base || '') + kind + '/' + slug + '/';
    };
    document.getElementById('cgo').addEventListener('click', go);
    input.addEventListener('keydown', function (e) { if (e.key === 'Enter') { e.preventDefault(); go(); } });
  }
  var f = document.getElementById('cfilter');
  if (f) {
    f.addEventListener('input', function () {
      var q = f.value.trim().toLowerCase();
      document.querySelectorAll('.crow').forEach(function (r) { r.style.display = !q || r.dataset.name.indexOf(q) > -1 ? '' : 'none'; });
      document.querySelectorAll('.region').forEach(function (g) {
        var any = Array.prototype.some.call(g.querySelectorAll('.crow'), function (r) { return r.style.display !== 'none'; });
        g.style.display = any ? '' : 'none';
      });
    });
  }
})();
