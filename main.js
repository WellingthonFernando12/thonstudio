const cursor = document.querySelector(".cursor");
const interactiveItems = document.querySelectorAll("a, button, .link-card");

if (cursor) {
  window.addEventListener("pointermove", (event) => {
    cursor.classList.add("is-ready");
    cursor.style.transform = `translate(${event.clientX}px, ${event.clientY}px) translate(-50%, -50%)`;
  });

  interactiveItems.forEach((item) => {
    item.addEventListener("pointerenter", () => cursor.classList.add("is-hovering"));
    item.addEventListener("pointerleave", () => cursor.classList.remove("is-hovering"));
  });
}

document.querySelectorAll(".link-card").forEach((card) => {
  card.addEventListener("pointermove", (event) => {
    const rect = card.getBoundingClientRect();
    const x = ((event.clientX - rect.left) / rect.width) * 100;
    const y = ((event.clientY - rect.top) / rect.height) * 100;
    card.style.setProperty("--x", `${x}%`);
    card.style.setProperty("--y", `${y}%`);
  });

  card.addEventListener("click", () => {
    const label = card.getAttribute("data-track");
    if (label) console.info(`Link clicked: ${label}`);
  });
});
