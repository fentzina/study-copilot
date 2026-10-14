const $ = (id) => document.getElementById(id);
const status = $("status");

function el(tag, text, cls) {
  const e = document.createElement(tag);
  if (text !== undefined) e.textContent = text;
  if (cls) e.className = cls;
  return e;
}

document.querySelectorAll(".tabs button").forEach((btn) => {
  btn.onclick = () => {
    document.querySelectorAll(".tabs button").forEach((b) => b.setAttribute("aria-selected", b === btn));
    ["summary", "cards", "quiz"].forEach((id) => ($(id).hidden = id !== btn.dataset.tab));
  };
});

$("go").onclick = async () => {
  const file = $("pdf").files[0];
  status.className = "";
  if (!file) { status.textContent = "Επίλεξε πρώτα ένα PDF."; status.className = "error"; return; }
  const form = new FormData();
  form.append("pdf", file);
  form.append("private", $("private").checked ? "1" : "0");
  status.textContent = "Δουλεύω πάνω στις διαφάνειες... (μπορεί να πάρει λίγο)";
  $("go").disabled = true;
  try {
    const res = await fetch("/api/analyze", { method: "POST", body: form });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Κάτι πήγε στραβά.");
    render(data);
    status.textContent = "Έτοιμο.";
  } catch (err) {
    status.textContent = err.message;
    status.className = "error";
  } finally {
    $("go").disabled = false;
  }
};

function render(d) {
  $("results").hidden = false;

  const ul = el("ul");
  d.summary.forEach((s) => {
    const li = el("li", s.text + " ");
    li.append(el("span", `(σελ. ${s.page})`, "page"));
    ul.append(li);
  });
  $("summary").replaceChildren(ul);

  const cards = $("cards");
  cards.replaceChildren();
  d.flashcards.forEach((c) => {
    const b = el("button", c.front, "card");
    b.setAttribute("aria-label", "Γύρνα την κάρτα");
    let flipped = false;
    b.onclick = () => {
      flipped = !flipped;
      b.textContent = flipped ? c.back : c.front;
      b.classList.toggle("flipped", flipped);
    };
    cards.append(b);
  });

  const quiz = $("quiz");
  quiz.replaceChildren();
  d.quiz.forEach((q, i) => {
    const fs = el("fieldset", undefined, "q");
    fs.append(el("legend", `${i + 1}. ${q.question}`));
    q.options.forEach((opt, j) => {
      const label = el("label");
      const input = el("input");
      input.type = "radio"; input.name = "q" + i; input.value = j;
      label.append(input, " " + opt);
      fs.append(label);
    });
    fs.append(el("div", "", "explain"));
    quiz.append(fs);
  });
  const finish = el("button", "Δες το σκορ");
  const score = el("div", "");
  score.id = "score";
  finish.onclick = () => {
    let right = 0;
    d.quiz.forEach((q, i) => {
      const chosen = document.querySelector(`input[name=q${i}]:checked`);
      const ok = chosen && Number(chosen.value) === q.correct_index;
      if (ok) right++;
      const box = quiz.children[i].querySelector(".explain");
      box.className = "explain " + (ok ? "right" : "wrong");
      box.textContent = (ok ? "Σωστό. " : `Λάθος. Σωστή απάντηση: ${q.options[q.correct_index]}. `) +
        `${q.explanation} (σελ. ${q.page})`;
    });
    score.textContent = `Σκορ: ${right} / ${d.quiz.length}`;
  };
  quiz.append(finish, score);
}
