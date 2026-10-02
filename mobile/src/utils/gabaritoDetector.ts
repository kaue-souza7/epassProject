import type { MarkerResult, DetectionResult } from "../types/gabarito";
import { FOLHA_TEMPLATE } from "./folhaTemplate";

const QUADRANT_SEARCH_W = 100;
const QUADRANT_SEARCH_H = 100;
const WINDOW_SIZE = 8;
const BRIGHTNESS_THRESHOLD = 100;

export function buildDetectorHtml(base64: string): string {
  const q = FOLHA_TEMPLATE;
  const w = q.imageWidth;
  const h = q.imageHeight;

  const quadrants = [
    { name: "TL", cx: q.marcadores[0].cx, cy: q.marcadores[0].cy },
    { name: "TR", cx: q.marcadores[1].cx, cy: q.marcadores[1].cy },
    { name: "BL", cx: q.marcadores[2].cx, cy: q.marcadores[2].cy },
    { name: "BR", cx: q.marcadores[3].cx, cy: q.marcadores[3].cy },
  ];

  const quadJS = JSON.stringify(quadrants);

  return `
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { background: #1a1a2e; display: flex; justify-content: center; align-items: center; min-height: 100vh; font-family: -apple-system, sans-serif; }
  .container { max-width: 100%; padding: 12px; }
  canvas { display: block; width: 100%; height: auto; border-radius: 12px; box-shadow: 0 4px 24px rgba(0,0,0,0.5); }
  .status { margin-top: 16px; text-align: center; }
  .status-text { font-size: 18px; font-weight: 700; color: #fff; }
  .status-text.ok { color: #4CAF50; }
  .status-text.fail { color: #F44336; }
  .detail { font-size: 13px; color: rgba(255,255,255,0.6); margin-top: 4px; }
  .btn { margin-top: 20px; background: #6C63FF; color: #fff; border: none; border-radius: 28px; padding: 14px 32px; font-size: 16px; font-weight: 700; width: 100%; cursor: pointer; }
  .btn:disabled { opacity: 0.5; }
  .marker-table { margin-top: 12px; width: 100%; border-collapse: collapse; }
  .marker-table td { padding: 6px 8px; font-size: 12px; color: rgba(255,255,255,0.7); border-bottom: 1px solid rgba(255,255,255,0.1); }
  .marker-table td:first-child { font-weight: 700; }
  .dot-ok { color: #4CAF50; }
  .dot-fail { color: #F44336; }
</style>
</head>
<body>
<div class="container">
  <canvas id="c"></canvas>
  <div id="status" class="status">
    <div id="statusText" class="status-text">Processando imagem...</div>
    <div id="statusDetail" class="detail">Detectando marcadores da folha</div>
  </div>
  <table id="markerTable" class="marker-table" style="display:none">
    <tr><td></td><td>Esperado</td><td>Detectado</td><td></td></tr>
  </table>
  <button id="continueBtn" class="btn" disabled onclick="sendResult()">
    Confirmar e continuar
  </button>
</div>

<script>
  var detectionResult = null;

  function findDarkestWindow(ctx, startX, startY, searchW, searchH, windowSize) {
    var minBrightness = 255;
    var bestX = startX;
    var bestY = startY;

    var imageData = ctx.getImageData(startX, startY, searchW, searchH);
    var data = imageData.data;

    for (var y = 0; y <= searchH - windowSize; y++) {
      for (var x = 0; x <= searchW - windowSize; x++) {
        var sum = 0;
        var count = 0;
        for (var wy = 0; wy < windowSize; wy++) {
          for (var wx = 0; wx < windowSize; wx++) {
            var idx = ((y + wy) * searchW + (x + wx)) * 4;
            var r = data[idx];
            var g = data[idx + 1];
            var b = data[idx + 2];
            sum += (r + g + b) / 3;
            count++;
          }
        }
        var avgBrightness = sum / count;
        if (avgBrightness < minBrightness) {
          minBrightness = avgBrightness;
          bestX = startX + x + Math.floor(windowSize / 2);
          bestY = startY + y + Math.floor(windowSize / 2);
        }
      }
    }

    return { x: bestX, y: bestY, brightness: minBrightness };
  }

  function drawMarker(ctx, x, y, found) {
    var size = 16;
    ctx.save();
    ctx.strokeStyle = found ? '#4CAF50' : '#F44336';
    ctx.lineWidth = 3;

    // Crosshair
    ctx.beginPath();
    ctx.moveTo(x - size, y);
    ctx.lineTo(x + size, y);
    ctx.moveTo(x, y - size);
    ctx.lineTo(x, y + size);
    ctx.stroke();

    // Rectangle
    ctx.strokeRect(x - size/2, y - size/2, size, size);

    // Label
    ctx.fillStyle = found ? '#4CAF50' : '#F44336';
    ctx.font = 'bold 12px sans-serif';
    ctx.fillText(found ? 'OK' : 'FAIL', x + size + 4, y + 4);

    ctx.restore();
  }

  function processImage() {
    var canvas = document.getElementById('c');
    var ctx = canvas.getContext('2d');
    var img = new Image();
    img.onload = function() {
      canvas.width = img.width;
      canvas.height = img.height;
      ctx.drawImage(img, 0, 0);

      var quadrants = ${quadJS};
      var sw = ${QUADRANT_SEARCH_W};
      var sh = ${QUADRANT_SEARCH_H};
      var ws = ${WINDOW_SIZE};
      var threshold = ${BRIGHTNESS_THRESHOLD};

      var markers = [];

      quadrants.forEach(function(q) {
        var startX = Math.max(0, q.cx - Math.floor(sw / 2));
        var startY = Math.max(0, q.cy - Math.floor(sh / 2));
        var actualSW = Math.min(sw, img.width - startX);
        var actualSH = Math.min(sh, img.height - startY);

        var result = findDarkestWindow(ctx, startX, startY, actualSW, actualSH, ws);
        var found = result.brightness < threshold;
        markers.push({
          name: q.name,
          x: result.x,
          y: result.y,
          expectedCx: q.cx,
          expectedCy: q.cy,
          brightness: Math.round(result.brightness),
          found: found
        });
        drawMarker(ctx, result.x, result.y, found);
      });

      // Draw outline connecting found markers
      ctx.save();
      ctx.strokeStyle = '#6C63FF';
      ctx.lineWidth = 2;
      ctx.setLineDash([6, 4]);
      ctx.beginPath();
      markers.forEach(function(m, i) {
        if (i === 0) ctx.moveTo(m.x, m.y);
        else ctx.lineTo(m.x, m.y);
      });
      ctx.closePath();
      ctx.stroke();

      // Draw expected marker positions (dots)
      quadrants.forEach(function(q) {
        ctx.fillStyle = 'rgba(255,255,255,0.4)';
        ctx.beginPath();
        ctx.arc(q.cx, q.cy, 3, 0, Math.PI * 2);
        ctx.fill();
      });

      ctx.restore();

      var allFound = markers.every(function(m) { return m.found; });
      var foundCount = markers.filter(function(m) { return m.found; }).length;
      detectionResult = { markers: markers, allFound: allFound, foundCount: foundCount };

      // Update status
      var statusEl = document.getElementById('statusText');
      var detailEl = document.getElementById('statusDetail');

      if (allFound) {
        statusEl.textContent = '✓ ' + foundCount + ' marcadores encontrados';
        statusEl.className = 'status-text ok';
        detailEl.textContent = 'Folha localizada com sucesso';
        document.getElementById('continueBtn').disabled = false;
      } else {
        statusEl.textContent = '✗ Apenas ' + foundCount + ' de 4 marcadores';
        statusEl.className = 'status-text fail';
        detailEl.textContent = 'Reposicione a folha e tente novamente';
      }

      // Draw marker table
      var tableEl = document.getElementById('markerTable');
      tableEl.style.display = 'table';
      markers.forEach(function(m) {
        var row = tableEl.insertRow();
        var c1 = row.insertCell();
        c1.innerHTML = '<span class="' + (m.found ? 'dot-ok' : 'dot-fail') + '">' + (m.found ? '✓' : '✗') + '</span> ' + m.name;
        var c2 = row.insertCell();
        c2.textContent = '(' + m.expectedCx + ', ' + m.expectedCy + ')';
        var c3 = row.insertCell();
        c3.textContent = '(' + m.x + ', ' + m.y + ')';
        var c4 = row.insertCell();
        c4.textContent = m.brightness.toFixed(0);
      });
    };
    img.src = 'data:image/jpeg;base64,' + '${base64}';
  }

  function sendResult() {
    if (detectionResult) {
      window.ReactNativeWebView.postMessage(JSON.stringify(detectionResult));
    }
  }

  processImage();
</script>
</body>
</html>`;
}
