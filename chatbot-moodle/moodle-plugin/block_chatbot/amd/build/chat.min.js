define([], function () {
    'use strict';

    var backendUrl = '';
    var token = '';
    var userId = 0;
    var currentSubject = '';

    function getUserIdFromToken(tok) {
        try {
            var parts = tok.split('.');
            var payload = parts[1];
            var padded = payload + '==='.slice((payload.length + 3) % 4);
            var decoded = atob(padded.replace(/-/g, '+').replace(/_/g, '/'));
            return JSON.parse(decoded).user_id || 0;
        } catch (e) {
            return 0;
        }
    }

    function appendMessage(role, content) {
        var container = document.getElementById('block-chatbot-messages');
        var welcome = document.getElementById('block-chatbot-welcome');
        if (welcome) {
            welcome.style.display = 'none';
        }

        var div = document.createElement('div');
        div.style.marginBottom = '8px';
        div.style.display = 'flex';
        div.style.justifyContent = role === 'user' ? 'flex-end' : 'flex-start';

        var bubble = document.createElement('div');
        bubble.style.maxWidth = '80%';
        bubble.style.padding = '6px 10px';
        bubble.style.borderRadius = '12px';
        bubble.style.fontSize = '0.85em';
        bubble.style.lineHeight = '1.4';
        bubble.style.whiteSpace = 'pre-wrap';
        bubble.style.wordBreak = 'break-word';

        if (role === 'user') {
            bubble.style.background = '#0d6efd';
            bubble.style.color = '#fff';
        } else {
            bubble.style.background = '#e9ecef';
            bubble.style.color = '#212529';
        }

        bubble.textContent = content;
        div.appendChild(bubble);
        container.appendChild(div);
        container.scrollTop = container.scrollHeight;
    }

    function appendTypingIndicator() {
        var container = document.getElementById('block-chatbot-messages');
        var div = document.createElement('div');
        div.id = 'block-chatbot-typing';
        div.style.marginBottom = '8px';
        div.style.display = 'flex';
        div.style.justifyContent = 'flex-start';

        var bubble = document.createElement('div');
        bubble.style.padding = '6px 10px';
        bubble.style.borderRadius = '12px';
        bubble.style.fontSize = '0.85em';
        bubble.style.background = '#e9ecef';
        bubble.style.color = '#6c757d';
        bubble.textContent = '...';

        div.appendChild(bubble);
        container.appendChild(div);
        container.scrollTop = container.scrollHeight;
    }

    function removeTypingIndicator() {
        var el = document.getElementById('block-chatbot-typing');
        if (el) {
            el.parentNode.removeChild(el);
        }
    }

    function sendMessage() {
        var input = document.getElementById('block-chatbot-input');
        var text = input.value.trim();
        if (!text) {
            return;
        }

        input.value = '';
        appendMessage('user', text);
        appendTypingIndicator();

        var body = { message: text, token: token };
        if (currentSubject) {
            body.subject = currentSubject;
        }

        fetch(backendUrl + '/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        })
        .then(function (res) {
            if (res.status === 429) {
                return { reply: 'Has alcanzado el límite diario de mensajes. Vuelve mañana.', suggest_exercise: false };
            }
            if (!res.ok) {
                return { reply: 'Error del servidor. Inténtalo de nuevo más tarde.', suggest_exercise: false };
            }
            return res.json();
        })
        .then(function (data) {
            removeTypingIndicator();
            appendMessage('assistant', data.response);

            var exerciseBtn = document.getElementById('block-chatbot-exercise-btn');
            if (data.suggest_exercise && exerciseBtn) {
                exerciseBtn.style.display = 'inline-block';
            }
        })
        .catch(function () {
            removeTypingIndicator();
            appendMessage('assistant', 'No se pudo conectar con el asistente. Comprueba tu conexión.');
        });
    }

    function requestExercise() {
        var subject = currentSubject || 'Matemáticas';
        appendTypingIndicator();

        fetch(backendUrl + '/exercise', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ token: token, topic: subject, subject: subject })
        })
        .then(function (res) {
            return res.ok ? res.json() : null;
        })
        .then(function (data) {
            removeTypingIndicator();
            if (!data) {
                appendMessage('assistant', 'No pude generar un ejercicio. Inténtalo de nuevo.');
                return;
            }

            appendMessage('assistant', 'Ejercicio de ' + subject + ':\n\n' + data.question);

            var input = document.getElementById('block-chatbot-input');
            input.placeholder = 'Escribe tu respuesta al ejercicio...';
            input.dataset.exerciseId = data.exercise_id;
        })
        .catch(function () {
            removeTypingIndicator();
            appendMessage('assistant', 'Error al solicitar el ejercicio.');
        });
    }

    function submitExerciseAnswer(exerciseId, answerText) {
        appendTypingIndicator();

        fetch(backendUrl + '/exercise/answer', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ exercise_id: parseInt(exerciseId, 10), answer: answerText, token: token })
        })
        .then(function (res) {
            return res.ok ? res.json() : null;
        })
        .then(function (data) {
            removeTypingIndicator();
            if (!data) {
                appendMessage('assistant', 'Error al evaluar tu respuesta.');
                return;
            }

            var prefix = data.correct ? '¡Correcto! ' : 'No del todo. ';
            appendMessage('assistant', prefix + data.feedback);

            var input = document.getElementById('block-chatbot-input');
            input.placeholder = 'Escribe tu pregunta...';
            delete input.dataset.exerciseId;
        })
        .catch(function () {
            removeTypingIndicator();
            appendMessage('assistant', 'Error al enviar tu respuesta.');
        });
    }

    function loadProgress() {
        var panel = document.getElementById('block-chatbot-progress-panel');
        if (!panel) {
            return;
        }

        panel.innerHTML = '<em>Cargando...</em>';

        fetch(backendUrl + '/progress/' + userId + '?token=' + encodeURIComponent(token))
        .then(function (res) {
            return res.ok ? res.json() : null;
        })
        .then(function (data) {
            if (!data) {
                panel.innerHTML = '<em>No se pudo cargar el progreso.</em>';
                return;
            }

            var html = '<strong>Mi progreso</strong><br>';
            html += 'Mensajes hoy: ' + data.messages_today + '<br>';
            html += 'Ejercicios resueltos: ' + data.total_exercises;
            if (data.total_exercises > 0) {
                var pct = Math.round((data.correct_exercises / data.total_exercises) * 100);
                html += ' (' + pct + '% correctos)';
            }

            if (data.subjects && data.subjects.length > 0) {
                html += '<br><br><strong>Por materia:</strong><br>';
                data.subjects.forEach(function (s) {
                    html += '· ' + s.subject + ': ' + s.count + ' consultas<br>';
                });
            }

            panel.innerHTML = html;
        })
        .catch(function () {
            panel.innerHTML = '<em>Error al cargar el progreso.</em>';
        });
    }

    return {
        init: function (params) {
            backendUrl = params.backendUrl || '';
            token = params.token || '';
            userId = params.userId || getUserIdFromToken(token);

            var sendBtn = document.getElementById('block-chatbot-send');
            var input = document.getElementById('block-chatbot-input');
            var subjectSel = document.getElementById('block-chatbot-subject');
            var exerciseBtn = document.getElementById('block-chatbot-exercise-btn');
            var progressToggle = document.getElementById('block-chatbot-progress-toggle');
            var progressPanel = document.getElementById('block-chatbot-progress-panel');

            if (sendBtn) {
                sendBtn.addEventListener('click', function () {
                    var exerciseId = input && input.dataset.exerciseId;
                    if (exerciseId) {
                        var ans = input.value.trim();
                        if (ans) {
                            input.value = '';
                            appendMessage('user', ans);
                            submitExerciseAnswer(exerciseId, ans);
                        }
                    } else {
                        sendMessage();
                    }
                });
            }

            if (input) {
                input.addEventListener('keydown', function (e) {
                    if (e.key === 'Enter') {
                        e.preventDefault();
                        sendBtn && sendBtn.click();
                    }
                });
            }

            if (subjectSel) {
                subjectSel.addEventListener('change', function () {
                    currentSubject = subjectSel.value;
                    var exerciseBtnEl = document.getElementById('block-chatbot-exercise-btn');
                    if (exerciseBtnEl) {
                        exerciseBtnEl.style.display = currentSubject ? 'inline-block' : 'none';
                    }
                });
            }

            if (exerciseBtn) {
                exerciseBtn.addEventListener('click', function () {
                    requestExercise();
                });
            }

            if (progressToggle && progressPanel) {
                progressToggle.addEventListener('click', function () {
                    if (progressPanel.style.display === 'none') {
                        progressPanel.style.display = 'block';
                        loadProgress();
                    } else {
                        progressPanel.style.display = 'none';
                    }
                });
            }
        }
    };
});
