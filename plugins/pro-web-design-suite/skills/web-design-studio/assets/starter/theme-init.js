/* The no-flash theme script. Inline it in <head>, before the stylesheets:
   it must run before the first paint, so it cannot be a deferred file.

     <script> ...the function below... </script>

   It sets data-theme from the stored choice, or from the OS, so the tokens
   and the native controls flip together (tokens.css, the DARK THEME block).
   localStorage can throw (blocked storage, some private modes); the OS
   preference is the fallback then. */
(function () {
  var theme;
  try {
    theme = localStorage.getItem('theme');
  } catch (e) {
    theme = null;
  }
  if (theme !== 'light' && theme !== 'dark') {
    theme = matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }
  document.documentElement.dataset.theme = theme;
})();
