let map = L.map('map').setView([23.6, 58.5], 7);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);

let resultData = [];

function upload() {
  const files = document.getElementById("fileInput").files;
  let fd = new FormData();

  for (let f of files) fd.append("files", f);

  fetch("/upload", { method: "POST", body: fd })
    .then(r => r.json())
    .then(data => {
      resultData = data.details;

      document.getElementById("summary").textContent =
        `Paths: ${data.paths}
Declared Total: ${data.declared_total} m
Calculated Total: ${data.calculated_total} m
Difference: ${data.difference_total} m

${data.equation}`;

      let table = document.getElementById("table");
      table.innerHTML = `
      <tr>
        <th>Name</th><th>Declared</th><th>Calculated</th>
        <th>Diff</th><th>Diff %</th>
      </tr>`;

      data.details.forEach(d => {
        table.innerHTML += `
        <tr>
          <td>${d.name}</td>
          <td>${d.declared_m ?? "-"}</td>
          <td>${d.calculated_m}</td>
          <td>${d.difference_m ?? "-"}</td>
          <td>${d.difference_pct ?? "-"}</td>
        </tr>`;
      });

      map.eachLayer(l => l instanceof L.Polyline && map.removeLayer(l));
      data.coordinates.forEach(line => L.polyline(line).addTo(map));
    });
}

function exportFile(fmt) {
  fetch(`/export/${fmt}`, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(resultData)
  })
  .then(res => res.blob())
  .then(blob => {
    let a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `results.${fmt}`;
    a.click();
  });
}
