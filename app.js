const form = document.querySelector("#controls");
const status = document.querySelector("#status");
const result = document.querySelector("#result");
const submit = form.querySelector("button");

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  submit.disabled = true;
  result.hidden = true;
  status.textContent = "Extracting colors…";

  try {
    const file = document.querySelector("#photo").files[0];
    const sample = file ? null : await fetch("/sample");
    if (sample && !sample.ok) throw new Error("The sample could not be loaded.");
    const body = file ?? await sample.blob();
    const colors = document.querySelector("#colors").value;
    const response = await fetch("/api/palette?" + new URLSearchParams({ colors }), {
      method: "POST",
      body,
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error);

    document.querySelector("#original").src = data.original;
    document.querySelector("#reduced").src = data.reduced;
    document.querySelector("#download").href = data.reduced;
    const swatches = data.palette.map(({ hex, percent }) => {
      const item = document.createElement("li");
      const swatch = document.createElement("span");
      swatch.className = "swatch";
      swatch.style.backgroundColor = hex;
      swatch.setAttribute("aria-hidden", "true");
      item.append(swatch, document.createTextNode(hex.toUpperCase() + " · " + percent + "%"));
      return item;
    });
    document.querySelector("#palette").replaceChildren(...swatches);
    status.textContent = data.palette.length + " colors · " + data.width + " × " +
      data.height + " preview · RGB error (RMSE) " + data.rgb_rmse + " / 255";
    result.hidden = false;
  } catch (error) {
    status.textContent = error.message;
  } finally {
    submit.disabled = false;
  }
});
