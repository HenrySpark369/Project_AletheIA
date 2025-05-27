
let ultimoTimestamp = null;
let nuevosHTML = "";

function actualizarFeed() {
  fetch('/feed_fragment?desde=' + encodeURIComponent(ultimoTimestamp || ""))
    .then(response => response.text())
    .then(html => {
      if (html.trim()) {
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = html;
        const nuevos = tempDiv.querySelectorAll('[data-timestamp]').length;

        if (nuevos > 0) {
          nuevosHTML = html;
          document.getElementById("contador-nuevos").innerText = `${nuevos}`;
          document.getElementById("nuevo-post-alerta").style.display = "block";
          const timestamps = Array.from(tempDiv.querySelectorAll('[data-timestamp]'))
            .map(el => el.getAttribute('data-timestamp'))
            .sort(); // Asegura orden ascendente

          if (timestamps.length > 0) {
            ultimoTimestamp = timestamps[timestamps.length - 1]; // El más reciente
          }
        }
      }
    });
}

function mostrarNuevosPosts() {
  const container = document.getElementById("feed-container");
  const tempDiv = document.createElement('div');
  tempDiv.innerHTML = nuevosHTML;

  tempDiv.querySelectorAll('[data-timestamp]').forEach(post => {
    const ts = post.getAttribute('data-timestamp');
    if (!container.querySelector(`[data-timestamp="${ts}"]`)) {
      container.insertAdjacentElement('afterbegin', post);
    }
  });

  // Actualiza último timestamp
  const nuevosTimestamps = Array.from(tempDiv.querySelectorAll('[data-timestamp]'))
    .map(el => el.getAttribute('data-timestamp'))
    .sort();
  if (nuevosTimestamps.length > 0) {
    ultimoTimestamp = nuevosTimestamps[nuevosTimestamps.length - 1];
  }

  document.getElementById("nuevo-post-alerta").style.display = "none";
  nuevosHTML = "";
}

window.onload = () => {
  const primerPost = document.querySelector('[data-timestamp]');
  if (primerPost) {
    ultimoTimestamp = primerPost.getAttribute('data-timestamp');
  }
  setInterval(actualizarFeed, 5000);
};
