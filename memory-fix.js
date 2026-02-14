document.addEventListener('DOMContentLoaded', function() {
  var old = window.fetch;
  window.fetch = function(url, opts) {
    if (url && url.indexOf('api.cosmic-claw.com') !== -1) {
      return old('https://dzongy.github.io/tcc-sovereignty-lite/zenith-memory.json');
    }
    return old.apply(this, arguments);
  };
});
