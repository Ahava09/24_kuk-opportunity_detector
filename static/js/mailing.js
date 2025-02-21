document.addEventListener("DOMContentLoaded", function () {
    document.querySelector("button").addEventListener("click", fetchEmails);
});

function fetchEmails() {
    const email = document.getElementById("email").value;
    const password = document.getElementById("password").value;
    const loading = document.getElementById("loading");
    const fetchButton = document.getElementById("fetchButton");
    const emailContainer = document.getElementById("emails");

    // Afficher le loader et désactiver le bouton
    loading.style.display = "block";
    fetchButton.disabled = true;
    emailContainer.innerHTML = ""; // Effacer les anciens emails

    fetch("http://localhost:5000/get_emails", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password })
    })
    .then(response => response.json())
    .then(data => {
        let emailList = "<h3>Emails reçus :</h3>";
        data.forEach(mail => {
            emailList += `<p><b>${mail.subject}</b> de ${mail.from}<br>🗂 Pièces jointes : ${mail.attachments}</p><hr>`;
        });

        emailContainer.innerHTML = emailList;
    })
    .catch(error => {
        emailContainer.innerHTML = `<p style="color:red;">Erreur : Impossible de récupérer les emails.</p>`;
        console.error("Erreur :", error);
    })
    .finally(() => {
        // Cacher le loader et réactiver le bouton
        loading.style.display = "none";
        fetchButton.disabled = false;
    });
}