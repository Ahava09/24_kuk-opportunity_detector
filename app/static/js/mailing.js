document.addEventListener("DOMContentLoaded", function () {
    displayEmails();
});

function displayEmails() {
    const emailContainer = document.getElementById("emails");
    emailContainer.style.display = "flex";
    const unreadCount = document.getElementById("unreadCount");
    const messageIcon = document.getElementById("messageIcon");

    // Récupérer les emails du localStorage
    const emails = JSON.parse(localStorage.getItem("emails") || "[]");
    const unreadEmails = localStorage.getItem("unread_count") || 0;

    // Afficher les emails
    if (emails.length > 0) {
        let emailList = "";

        emails.forEach(mail => {
            emailList += `
                <div class="email-item">
                    <p><b>${mail.subject}</b> de ${mail.from}</p>
                    <p>📆 Reçu le : ${mail.receive_at}</p>
                    <p>Body : ${mail.body}</p>
                    <p>📌 Negoce : ${mail.is_negoce ? "✅ Oui" : "❌ Non"}</p>
                </div>
            `;
        });

        emailContainer.innerHTML = emailList;

        // Mettre à jour l'icône des messages non lus
        if (unreadEmails > 0) {
            messageIcon.style.display = "flex";
            unreadCount.textContent = unreadEmails;
        }
    } else {
        emailContainer.innerHTML = "<p>Aucun email non lu trouvé.</p>";
        messageIcon.style.display = "none";
    }
}

document.getElementById("messageIcon").addEventListener("click", function () {
    const emailContainer = document.getElementById("emails");

    // Vérifier si la liste est cachée
    if (emailContainer.style.display === "none" || emailContainer.style.display === "") {
        // emailContainer.style.display = "flex";
        displayEmails();
          
    } else {
        emailContainer.style.display = "none";   
    }
});

document.getElementById("searchForm").addEventListener("submit", function (event) {
    event.preventDefault(); 

    const searchCriteria = document.getElementById("searchCriteria").value.trim();
    const emailContainer = document.getElementById("emails");

    if (searchCriteria === "") {
        alert("Veuillez entrer un critère de recherche.");
        return;
    }

    fetch(`api/searchCriteria?criterion=${encodeURIComponent(searchCriteria)}`, {
        method: "GET",
        headers: { "Content-Type": "application/json" }
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            emailContainer.innerHTML = `<p style="color:red;">❌ ${data.error}</p>`;
            return;
        }

        if (data.count === 0) {
            emailContainer.innerHTML = "<p>Aucun email trouvé.</p>";
            return;
        }

        let emailList = `<h3>📩 Résultats (${data.count}) :</h3>`;
        data.emails.forEach(mail => {
            emailList += `
                <div class="email-item">
                    <p><b>${mail.subject}</b> de ${mail.from}</p>
                    <p>📆 Reçu le : ${mail.receive_at}</p>
                    <p>📌 Negoce : ${mail.is_negoce ? "✅ Oui" : "❌ Non"}</p>
                </div>
            `;
        });

        emailContainer.innerHTML = emailList;
    })
    .catch(error => {
        console.error("Erreur :", error);
        emailContainer.innerHTML = `<p style="color:red;">❌ Erreur de récupération des emails.</p>`;
    });
});
