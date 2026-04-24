<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🧠 CHAPELET TAZZZ BOT</title>
    <style>
        * {
            box-sizing: border-box;
        }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1e2b3c 0%, #0f1a24 100%);
            margin: 0;
            padding: 20px;
            color: #f0f0f0;
            min-height: 100vh;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            background: rgba(255,255,255,0.1);
            backdrop-filter: blur(10px);
            border-radius: 24px;
            padding: 25px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.2);
        }
        h1, h2 {
            text-align: center;
            margin-bottom: 20px;
            font-weight: 300;
        }
        h1 {
            font-size: 2.2rem;
            letter-spacing: 2px;
        }
        .mode-selector {
            display: flex;
            gap: 15px;
            justify-content: center;
            margin-bottom: 30px;
            flex-wrap: wrap;
        }
        .mode-btn {
            background: #2c3e4e;
            border: none;
            color: white;
            padding: 12px 24px;
            border-radius: 40px;
            cursor: pointer;
            font-size: 1rem;
            transition: all 0.3s ease;
            font-weight: bold;
        }
        .mode-btn.active {
            background: #e67e22;
            box-shadow: 0 0 15px rgba(230,126,34,0.5);
        }
        .mode-btn:hover {
            transform: translateY(-2px);
        }
        .mode-panel {
            display: none;
            animation: fadeIn 0.4s ease;
        }
        .mode-panel.active-panel {
            display: block;
        }
        textarea, input[type="text"] {
            width: 100%;
            padding: 12px;
            margin: 10px 0;
            border-radius: 12px;
            border: none;
            background: #f0f0f0;
            font-size: 1rem;
            font-family: inherit;
        }
        .defauts-group {
            display: flex;
            flex-direction: column;
            gap: 10px;
            margin: 15px 0;
        }
        .defauts-group input {
            background: #fff;
            color: #1e2b3c;
        }
        button.generate {
            background: #e67e22;
            border: none;
            color: white;
            padding: 14px 28px;
            font-size: 1.2rem;
            border-radius: 40px;
            cursor: pointer;
            width: 100%;
            margin-top: 20px;
            transition: background 0.2s;
            font-weight: bold;
        }
        button.generate:hover {
            background: #d35400;
        }
        .loader {
            display: none;
            text-align: center;
            margin: 20px 0;
        }
        .loader.show {
            display: block;
        }
        .result {
            background: #0b1620;
            border-radius: 20px;
            padding: 20px;
            margin-top: 30px;
            white-space: pre-wrap;
            font-family: monospace;
            font-size: 0.9rem;
            max-height: 500px;
            overflow-y: auto;
            border-left: 5px solid #e67e22;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px);}
            to { opacity: 1; transform: translateY(0);}
        }
        footer {
            text-align: center;
            margin-top: 30px;
            font-size: 0.8rem;
            opacity: 0.7;
        }
        .copyright {
            font-size: 0.7rem;
            margin-top: 10px;
            text-align: center;
            opacity: 0.6;
        }
    </style>
</head>
<body>
<div class="container">
    <h1>🧠 CHAPELET TAZZZ BOT 📿</h1>
    <h2>Transforme ta structure mentale</h2>

    <div class="mode-selector">
        <button class="mode-btn" data-mode="expertise">📚 Expertise (7 jours)</button>
        <button class="mode-btn" data-mode="personnel">🔥 Développement personnel (21/66j)</button>
        <button class="mode-btn" data-mode="consultation">💬 Consultation guidée</button>
    </div>

    <!-- Mode Expertise -->
    <div id="expertise" class="mode-panel">
        <p>🔬 Quel domaine souhaites-tu maîtriser ?</p>
        <input type="text" id="domaine" placeholder="Ex: Recherche clinique, Python, IT support niveau 1 et 2...">
    </div>

    <!-- Mode Personnel -->
    <div id="personnel" class="mode-panel">
        <p>📝 Saisis les 5 défauts que tu souhaites corriger :</p>
        <div class="defauts-group" id="defauts-list">
            <!-- 5 inputs créés en JS -->
        </div>
    </div>

    <!-- Mode Consultation -->
    <div id="consultation" class="mode-panel">
        <p>💬 Parle-moi de tes difficultés, de ce qui te bloque, de ce que tu aimerais changer.</p>
        <textarea id="consult-message" rows="4" placeholder="Ex: Je veux maîtriser les concepts du IT support niveau 1 et 2 pour un entretien..."></textarea>
    </div>

    <button class="generate" id="generateBtn">✨ GÉNÉRER MON CHAPELET ✨</button>

    <div class="loader" id="loader">
        <div>⏳ Génération en cours... (20-40 secondes)</div>
    </div>

    <div id="result" class="result" style="display:none;"></div>
    <div class="copyright">© Dr Tazemda – Chapelet Taz Bot</div>
</div>

<script>
    // Gestion des modes
    const modeBtns = document.querySelectorAll('.mode-btn');
    const panels = {
        expertise: document.getElementById('expertise'),
        personnel: document.getElementById('personnel'),
        consultation: document.getElementById('consultation')
    };
    let currentMode = 'expertise';

    // Créer 5 inputs pour le mode personnel
    const defautsContainer = document.getElementById('defauts-list');
    for (let i = 1; i <= 5; i++) {
        const input = document.createElement('input');
        input.type = 'text';
        input.placeholder = `Défaut ${i} (ex: Je me lève tard)`;
        input.classList.add('defaut-input');
        defautsContainer.appendChild(input);
    }

    modeBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            modeBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            const mode = btn.getAttribute('data-mode');
            currentMode = mode;
            Object.keys(panels).forEach(key => {
                panels[key].classList.remove('active-panel');
            });
            panels[mode].classList.add('active-panel');
        });
    });
    // Activer expertise par défaut
    modeBtns[0].classList.add('active');
    panels.expertise.classList.add('active-panel');

    // Génération
    const generateBtn = document.getElementById('generateBtn');
    const loader = document.getElementById('loader');
    const resultDiv = document.getElementById('result');

    generateBtn.addEventListener('click', async () => {
        let payload = { mode: currentMode };
        if (currentMode === 'expertise') {
            const domaine = document.getElementById('domaine').value.trim();
            if (!domaine) {
                alert('Veuillez entrer un domaine.');
                return;
            }
            payload.domaine = domaine;
        } else if (currentMode === 'personnel') {
            const inputs = document.querySelectorAll('.defaut-input');
            const defauts = [];
            inputs.forEach(inp => {
                if (inp.value.trim()) defauts.push(inp.value.trim());
            });
            if (defauts.length !== 5) {
                alert('Veuillez remplir les 5 défauts.');
                return;
            }
            payload.defauts = defauts;
        } else if (currentMode === 'consultation') {
            const message = document.getElementById('consult-message').value.trim();
            if (!message) {
                alert('Veuillez décrire votre situation.');
                return;
            }
            payload.message = message;
        }

        loader.classList.add('show');
        resultDiv.style.display = 'none';
        resultDiv.innerHTML = '';

        try {
            const response = await fetch('/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await response.json();
            if (data.error) {
                alert('Erreur : ' + data.error);
            } else {
                // Afficher le chapelet avec un formatage propre (sauts de ligne conservés)
                resultDiv.innerHTML = data.chapelet.replace(/\n/g, '<br>');
                resultDiv.style.display = 'block';
            }
        } catch (err) {
            alert('Erreur réseau : ' + err.message);
        } finally {
            loader.classList.remove('show');
        }
    });
</script>
</body>
</html>
