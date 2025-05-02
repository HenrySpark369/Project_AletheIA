
let ultimoTimestamp = null;
let nuevosHTML = "";

function actualizarFeed() {
  fetch('/feed_fragment?desde=' + encodeURIComponent(ultimoTimestamp || ""))
    .then(response => response.text())
    .then(html => {
      if (html.trim()) {
        nuevosHTML = html;

        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = html;
        const nuevos = tempDiv.querySelectorAll('[data-timestamp]').length;

        document.getElementById("contador-nuevos").innerText = `${nuevos}`;
        document.getElementById("nuevo-post-alerta").style.display = "block";
      }
    });
}

function mostrarNuevosPosts() {
  document.getElementById("feed-container").insertAdjacentHTML('afterbegin', nuevosHTML);

  const primerPost = document.querySelector('[data-timestamp]');
  if (primerPost) {
    ultimoTimestamp = primerPost.getAttribute('data-timestamp');
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
