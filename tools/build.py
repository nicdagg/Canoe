import sys
src, out = sys.argv[1], sys.argv[2]
s = open(src, encoding='utf-8').read()
def rep(old, new):
    global s
    assert s.count(old) == 1, old[:60]
    s = s.replace(old, new)

rep('<!doctype html><html><head>', '<!doctype html><html lang="en"><head>')
rep('</style></head><body>\n<title>Canoe Hull Designer</title>\n', '''</style>
<title>Canoe Hull Designer</title>
<meta name="description" content="Design, analyze and build canoe hulls: lines, hydrostatics, stability, drag, waves, mold and laminate.">
<meta name="theme-color" content="#EDF1F4" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#0D151C" media="(prefers-color-scheme: dark)">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<meta name="apple-mobile-web-app-title" content="Canoe">
<link rel="manifest" href="manifest.webmanifest">
<link rel="icon" type="image/png" sizes="32x32" href="icons/favicon-32.png">
<link rel="apple-touch-icon" href="icons/apple-touch-icon.png">
</head><body>
''')
# Off claude.ai there is no downloads capability: save files with the iPhone share sheet or a normal browser download.
rep('''      }, function () {});
    }
  } catch (e) {}
''', '''      }, function () {});
    } else {
      dl = { save: localSave }; $('v3-png').hidden = false;
    }
  } catch (e) {}
  function localSave(o) {
    var blob = o.data instanceof Blob ? o.data : new Blob([o.data], { type: /\\.csv$/.test(o.filename) ? 'text/csv' : /\\.svg$/.test(o.filename) ? 'image/svg+xml' : 'text/plain' });
    function link() {
      var a = document.createElement('a'), u = URL.createObjectURL(blob);
      a.href = u; a.download = o.filename; document.body.appendChild(a); a.click(); a.remove();
      setTimeout(function () { URL.revokeObjectURL(u); }, 60000);
    }
    try {
      var f = new File([blob], o.filename, { type: blob.type || 'application/octet-stream' });
      if (navigator.canShare && navigator.canShare({ files: [f] }) && /iPhone|iPad|iPod|Android/.test(navigator.userAgent)) {
        return navigator.share({ files: [f] }).catch(function (e) {
          if (e && e.name === 'AbortError') { var x = new Error('declined'); x.code = 'declined'; throw x; }
          link();
        });
      }
    } catch (e) {}
    link();
    return Promise.resolve();
  }
''')
rep("if (!db) return svUseLocal('Saved in this browser only. Open the designer signed in to claude.ai to keep designs with it.');",
    "if (!db) return svUseLocal('Saved in this browser only.');")
rep('''  syncUI();
  render();
})();
</script>''', '''  syncUI();
  render();
})();
if ('serviceWorker' in navigator && location.protocol === 'https:') {
  window.addEventListener('load', function () { navigator.serviceWorker.register('sw.js').catch(function () {}); });
}
</script>''')
open(out, 'w', encoding='utf-8').write(s)
