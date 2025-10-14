import os
import webbrowser


def build_html() -> str:
    return (
        """<!DOCTYPE html>
        <html lang="ru">
        <head>
          <meta charset="UTF-8">
          <meta name="viewport" content="width=device-width, initial-scale=1.0">
          <title>Бадминтон-корт</title>
          <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { 
              font-family: Arial, sans-serif; 
              background: linear-gradient(135deg, #e8f5e8 0%, #d4edda 100%);
              min-height: 100vh;
            }
            .container { max-width: 800px; margin: 0 auto; padding: 20px; }
            .court { 
              background: #4CAF50; 
              border: 3px solid #333; 
              border-radius: 10px; 
              position: relative; 
              height: 400px; 
              margin: 20px 0;
              background-image: url('./img/court.jpg');
              background-size: cover;
              background-position: center;
              background-repeat: no-repeat;
            }
            .net { 
              position: absolute; 
              left: 50%; 
              top: 0; 
              width: 3px; 
              height: 100%; 
              background: #fff; 
              transform: translateX(-50%);
              box-shadow: 0 0 5px rgba(0,0,0,0.3);
            }
            .half { 
              position: absolute; 
              top: 0; 
              width: 50%; 
              height: 100%; 
              cursor: pointer;
              transition: background-color 0.2s ease;
            }
            .half:hover {
              background-color: rgba(255, 255, 255, 0.1);
            }
            .half:active {
              background-color: rgba(255, 255, 255, 0.3);
              transform: scale(0.98);
            }
            .half.clicked {
              background-color: rgba(0, 255, 0, 0.3);
              animation: clickEffect 0.3s ease-out;
            }
            
            @keyframes clickEffect {
              0% { transform: scale(1); }
              50% { transform: scale(0.95); background-color: rgba(0, 255, 0, 0.5); }
              100% { transform: scale(1); }
            }
            .left { left: 0; }
            .right { right: 0; }
            .segments { display: flex; flex-direction: column; height: 100%; }
            .segment { flex: 1; display: flex; align-items: center; justify-content: center; position: relative; }
            .box { 
              text-align: center; 
              padding: 10px; 
              position: absolute;
              bottom: 10px;
              left: 50%;
              transform: translateX(-50%);
              width: 140px;
            }
            /* Специальное позиционирование для верхних сегментов */
            #top_left .box, #top_right .box {
              bottom: 100px;
            }
            
            /* Специальное позиционирование для нижних сегментов */
            #bottom_left .box, #bottom_right .box {
              bottom: calc(10px + 1.5 * 30px); /* 10px (исходный bottom) + 1.5 * высота поля */
            }
            .hint { color: #fff; font-size: 12px; margin-bottom: 5px; }
            input { padding: 5px; border: none; border-radius: 3px; width: 120px; }
            .server-indicator { 
              margin-bottom: 5px; 
              position: absolute;
              transition: transform 0.2s ease-in-out;
              top: calc(50% - 18.5px);
              left: 50%;
              transform: translate(-50%, -50%);
            }
            .server-indicator img { 
              width: 25px; 
              height: 25px; 
              border: 1px solid red; 
              background-color: yellow;
              display: block;
              border-radius: 50%;
              padding: 4px;
              box-sizing: border-box;
              object-fit: contain;
            }
            .controls { text-align: center; margin: 20px 0; }
            .controls button { margin: 0 10px; padding: 10px 20px; font-size: 16px; }
            .controls button:last-of-type { margin-top: 15px; }
            .start-game-btn {
              background-color: #4CAF50;
              color: white;
              border: none;
              padding: 15px 30px;
              font-size: 18px;
              font-weight: bold;
              border-radius: 8px;
              cursor: pointer;
              transition: all 0.3s ease;
            }
            .start-game-btn:disabled {
              background-color: #cccccc;
              color: #666666;
              cursor: not-allowed;
            }
            .start-game-btn:not(:disabled):hover {
              background-color: #45a049;
              transform: scale(1.05);
            }
            .scoreboard-container { 
              position: absolute;
              top: 50%;
              left: 50%;
              transform: translate(-50%, -50%);
              z-index: 10;
              pointer-events: none;
              display: flex;
              gap: 200px;
              align-items: center;
            }
            
            .score-left {
              transform: translateX(56px); /* Сдвиг вправо на 25% ширины цифры (224px * 0.25 = 56px) */
            }
            
            .score-right {
              transform: translateX(-112px); /* Сдвиг влево на половину ширины цифры */
            }
            
            .score-left, .score-right {
              font-size: 224px; 
              font-weight: bold; 
              text-align: center; 
              text-shadow: 7px 7px 14px rgba(0,0,0,0.8);
              padding: 20px 40px;
              min-width: 200px;
            }
            
            .score-left {
              color: #2196F3; /* Синий цвет для левой команды */
            }
            
            .score-right {
              color: #f44336; /* Красный цвет для правой команды */
            }
            
            .score-buttons-left, .score-buttons-right {
              display: none; /* Скрываем кнопки, так как счет теперь в центре корта */
            }
            .score-button { 
              font-size: 24px; 
              font-weight: bold; 
              width: 60px; 
              height: 60px; 
              border-radius: 50%; 
              border: 3px solid #4CAF50; 
              background-color: #4CAF50; 
              color: white; 
              cursor: pointer; 
              transition: all 0.2s ease;
            }
            .score-button:hover { 
              background-color: #45a049; 
              transform: scale(1.1); 
            }
            /* Специальные стили для кнопок "+" */
            #btnPlusLeft, #btnPlusRight {
              width: 200px;
              height: 90px;
              border-radius: 45px;
              font-size: 36px;
            }
            .minus-button {
              background-color: #f44336;
              border-color: #f44336;
            }
            .minus-button:hover {
              background-color: #da190b;
            }
            .footer { text-align: center; color: #666; font-size: 12px; margin-top: 20px; }
            
            /* Стили для модального окна победы */
            .modal {
              display: none;
              position: fixed;
              z-index: 1000;
              left: 0;
              top: 0;
              width: 100%;
              height: 100%;
              background-color: rgba(0,0,0,0.8);
              animation: fadeIn 0.3s;
            }
            
            .modal-content {
              background-color: #fff;
              margin: 10% auto;
              padding: 30px;
              border-radius: 20px;
              width: 80%;
              max-width: 500px;
              text-align: center;
              position: relative;
              animation: slideIn 0.3s;
            }
            
            .close {
              color: #aaa;
              float: right;
              font-size: 28px;
              font-weight: bold;
              position: absolute;
              right: 15px;
              top: 10px;
              cursor: pointer;
            }
            
            .close:hover {
              color: #000;
            }
            
            .victory-content {
              display: flex;
              flex-direction: column;
              align-items: center;
              gap: 20px;
            }
            
            .victory-image {
              width: 150px;
              height: 150px;
              object-fit: contain;
            }
            
            .victory-text {
              color: #4CAF50;
              font-size: 32px;
              margin: 0;
              font-weight: bold;
            }
            
            @keyframes fadeIn {
              from { opacity: 0; }
              to { opacity: 1; }
            }
            
            @keyframes slideIn {
              from { transform: translateY(-50px); opacity: 0; }
              to { transform: translateY(0); opacity: 1; }
            }
            
            /* Стили для журнала подач */
            .journal-container {
              position: fixed;
              right: 20px;
              top: 50%;
              transform: translateY(-50%);
              width: 300px;
              height: 400px;
              background-color: #fff;
              border: 2px solid #4CAF50;
              border-radius: 10px;
              box-shadow: 0 4px 8px rgba(0,0,0,0.2);
              z-index: 100;
              transition: all 0.3s ease;
              display: none; /* Скрываем по умолчанию */
            }
            
            .journal-container.visible {
              display: block; /* Показываем когда нужно */
            }
            
            .journal-container.expanded {
              width: 500px;
              height: 600px;
            }
            
            .journal-header {
              background-color: #4CAF50;
              color: white;
              padding: 10px 15px;
              border-radius: 8px 8px 0 0;
              display: flex;
              justify-content: space-between;
              align-items: center;
            }
            
            .journal-controls {
              display: flex;
              gap: 5px;
              align-items: center;
            }
            
            .match-input {
              width: 60px;
              padding: 2px 5px;
              border: 1px solid #ccc;
              border-radius: 3px;
              font-size: 12px;
              text-align: center;
            }
            
            .find-btn {
              background: none;
              border: none;
              color: white;
              font-size: 16px;
              cursor: pointer;
              padding: 5px;
              border-radius: 3px;
              transition: background-color 0.2s;
            }
            
            .find-btn:hover {
              background-color: rgba(255,255,255,0.2);
            }
            
            .journal-header h3 {
              margin: 0;
              font-size: 16px;
            }
            
            .expand-btn, .stats-btn {
              background: none;
              border: none;
              color: white;
              font-size: 18px;
              cursor: pointer;
              padding: 5px;
              border-radius: 3px;
              transition: background-color 0.2s;
            }
            
            .expand-btn:hover, .stats-btn:hover {
              background-color: rgba(255,255,255,0.2);
            }
            
            .journal-content {
              height: calc(100% - 50px);
              overflow-y: auto;
              padding: 10px;
            }
            
            .journal-entry {
              background-color: #f9f9f9;
              border: 1px solid #ddd;
              border-radius: 5px;
              padding: 8px;
              margin-bottom: 5px;
              font-size: 12px;
              line-height: 1.4;
            }
            
            .journal-entry.success {
              border-left: 4px solid #4CAF50;
            }
            
            .journal-entry.returned {
              border-left: 4px solid #ff9800;
            }
            
            .journal-placeholder {
              text-align: center;
              color: #666;
              font-style: italic;
              margin-top: 50px;
            }
            
            .entry-time {
              color: #666;
              font-weight: bold;
            }
            
            .entry-players {
              margin: 2px 0;
            }
            
            .entry-result {
              font-weight: bold;
            }
            
            .entry-result.success {
              color: #4CAF50;
            }
            
            .entry-result.returned {
              color: #ff9800;
            }
            
            .entry-score {
              font-size: 10px;
              color: #666;
              font-weight: bold;
              margin-top: 2px;
            }
            
            /* Стили для статистики */
            .stats-content h4, .stats-content h5 {
              color: #4CAF50;
              margin: 10px 0 5px 0;
            }
            
            .player-stats, .game-summary {
              background-color: #f0f0f0;
              border: 1px solid #ddd;
              border-radius: 5px;
              padding: 8px;
              margin: 5px 0;
              font-size: 11px;
              line-height: 1.3;
            }
            
            .player-stats {
              border-left: 3px solid #4CAF50;
            }
            
            .game-summary {
              border-left: 3px solid #2196F3;
            }
          </style>
        </head>
        <body>
          <div class="container">
            <h1>Бадминтон-корт</h1>
            
            
            <div class="controls">
              <button id="btnSave">Сохранить имена</button>
              <button id="btnUndo">Отменить</button>
              <button id="btnClear">Очистить всё</button>
              <button id="btnMoveShuttlecock">Переместить подачу</button>
              <button id="btnToggleJournal">📋 Журнал подач</button>
              <button id="btnStartGame" class="start-game-btn">Начать игру</button>
            </div>
            

            <div class="court">
              <div class="net"></div>
              
              <!-- Счет в центре корта -->
              <div class="scoreboard-container">
                <div class="score-left" id="scoreLeft">0</div>
                <div class="score-right" id="scoreRight">0</div>
              </div>
              
              <div class="half left" id="court_left" title="Кликните для увеличения счета левой команды">
                <div class="segments">
                  <div class="segment" id="top_left">
                    <div class="box">
                      <div class="server-indicator" title="Подаёт" style="display: none;"><img src="./img_01.png" alt="Подающий" /></div>
                      <input type="text" placeholder="Имя игрока" id="name_top_left" value="Алексей" />
                    </div>
                  </div>
                  <div class="segment" id="bottom_left">
                    <div class="box">
                      <div class="server-indicator" title="Подаёт" style="display: none;"><img src="./img_01.png" alt="Подающий" /></div>
                      <input type="text" placeholder="Имя игрока" id="name_bottom_left" value="Дмитрий" />
                    </div>
                  </div>
                </div>
              </div>

                <div class="half right" id="court_right" title="Кликните для увеличения счета правой команды">
                  <div class="segments">
                    <div class="segment" id="top_right">
                      <div class="box">
                        <div class="server-indicator" title="Подаёт"><img src="./img_01.png" alt="Подающий" /></div>
                        <input type="text" placeholder="Имя игрока" id="name_top_right" value="Сергей" />
                      </div>
                    </div>
                    <div class="segment" id="bottom_right">
                      <div class="box">
                        <div class="server-indicator" title="Подаёт" style="display: none;"><img src="./img_01.png" alt="Подающий" /></div>
                        <input type="text" placeholder="Имя игрока" id="name_bottom_right" value="Андрей" />
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div class="footer">Данные сохраняются в LocalStorage этого браузера. Картинка фона: background.jpg (поместите рядом с HTML).</div>
          </div>

          <!-- Журнал подач -->
          <div class="journal-container">
            <div class="journal-header">
              <h3>Журнал подач</h3>
              <div class="journal-controls">
                <input type="number" id="matchNumberInput" placeholder="№ матча" min="1" class="match-input">
                <button id="btnFindMatch" class="find-btn" title="Найти матч">🔍</button>
                <button id="btnShowStats" class="stats-btn" title="Статистика">📊</button>
                <button id="btnExpandJournal" class="expand-btn">📖</button>
              </div>
            </div>
            <div id="journalContent" class="journal-content">
              <div class="journal-placeholder">Журнал начнет заполняться после начала игры</div>
            </div>
          </div>

          <!-- Модальное окно для победы -->
          <div id="victoryModal" class="modal">
            <div class="modal-content">
              <span class="close" onclick="closeVictoryModal()">&times;</span>
              <div class="victory-content">
                <img src="./img_02.png" alt="Победа" class="victory-image">
                <h2 id="victoryMessage" class="victory-text">Победа!</h2>
              </div>
            </div>
          </div>

          <script>
            const ids = [
              'name_top_left', 'name_bottom_left',
              'name_top_right', 'name_bottom_right'
            ];
            let scoreLeft = 0;
            let scoreRight = 0;
            let shuttlecockPosition = 'top_right'; // Начальная позиция волана
            let gameStarted = false;
            let gameStartTime = null;
            let timerInterval = null;
            let journalEntries = [];
            let currentGameId = null;
            let gameEndTime = null;
            let gameHistory = []; // История состояний игры для отката
            let isAnimating = false;
            
            console.log('Скрипт загружен, gameStarted:', gameStarted);

            function saveGameState() {
              // Сохраняем текущее состояние в историю
              gameHistory.push({
                scoreLeft: scoreLeft,
                scoreRight: scoreRight,
                shuttlecockPosition: shuttlecockPosition,
                gameStarted: gameStarted
              });
              
              // Ограничиваем историю последними 50 состояниями
              if (gameHistory.length > 50) {
                gameHistory = gameHistory.slice(-50);
              }
            }

            function undoLastAction() {
              if (gameHistory.length === 0) {
                alert('Нет действий для отмены');
                return;
              }
              
              // Получаем предыдущее состояние
              const previousState = gameHistory.pop();
              
              // Восстанавливаем состояние
              scoreLeft = previousState.scoreLeft;
              scoreRight = previousState.scoreRight;
              shuttlecockPosition = previousState.shuttlecockPosition;
              gameStarted = previousState.gameStarted;
              
              // Обновляем интерфейс
              updateScoreboard();
              updateShuttlecockDisplay();
              checkGameReady();
              
              // Сохраняем в localStorage
              localStorage.setItem('court_score_left', String(scoreLeft));
              localStorage.setItem('court_score_right', String(scoreRight));
              localStorage.setItem('court_shuttlecock_position', shuttlecockPosition);
              
              // Если игра была остановлена, останавливаем таймер
              if (!gameStarted) {
                stopTimer();
              }
            }

            function load() {
              ids.forEach(id => {
                const v = localStorage.getItem('court_' + id);
                if (v !== null) document.getElementById(id).value = v;
                // Если поле пустое, оставляем тестовое имя из HTML
                if (document.getElementById(id).value.trim() === '') {
                  // Поле уже имеет значение из HTML, не перезаписываем
                }
              });
              const sL = localStorage.getItem('court_score_left');
              const sR = localStorage.getItem('court_score_right');
              const sP = localStorage.getItem('court_shuttlecock_position');
              scoreLeft = sL !== null ? parseInt(sL, 10) || 0 : 0;
              scoreRight = sR !== null ? parseInt(sR, 10) || 0 : 0;
              shuttlecockPosition = sP !== null ? sP : 'top_right';
              updateScoreboard();
              updateShuttlecockDisplay();
              checkGameReady();
            }

            function save() {
              ids.forEach(id => {
                const v = document.getElementById(id).value || '';
                localStorage.setItem('court_' + id, v);
              });
              localStorage.setItem('court_score_left', String(scoreLeft));
              localStorage.setItem('court_score_right', String(scoreRight));
              alert('Имена сохранены');
            }

            function clearAll() {
              ids.forEach(id => {
                localStorage.removeItem('court_' + id);
                document.getElementById(id).value = '';
              });
              scoreLeft = 0; scoreRight = 0;
              shuttlecockPosition = 'top_right';
              gameStarted = false;
              clearJournal();
              document.getElementById('btnStartGame').disabled = true;
              document.getElementById('btnStartGame').textContent = 'Начать игру';
              localStorage.removeItem('court_score_left');
              localStorage.removeItem('court_score_right');
              localStorage.removeItem('court_shuttlecock_position');
              updateScoreboard();
              updateShuttlecockDisplay();
            }

            function updateScoreboard() {
              document.getElementById('scoreLeft').textContent = scoreLeft;
              document.getElementById('scoreRight').textContent = scoreRight;
            }

            function checkVictory() {
              if (scoreLeft >= 21) {
                gameStarted = false;
                document.getElementById('btnStartGame').textContent = 'Игра завершена';
                setTimeout(() => {
                  showVictoryModal('Победила команда слева!');
                  // Сбрасываем счет после показа модального окна
                  setTimeout(() => {
                    scoreLeft = 0;
                    scoreRight = 0;
                    updateScoreboard();
                    localStorage.setItem('court_score_left', String(scoreLeft));
                    localStorage.setItem('court_score_right', String(scoreRight));
                    // Возвращаем кнопку в исходное состояние
                    document.getElementById('btnStartGame').textContent = 'Начать игру';
                    document.getElementById('btnStartGame').disabled = false;
                  }, 2000); // Сбрасываем через 2 секунды после показа модального окна
                }, 100);
                return true;
              }
              if (scoreRight >= 21) {
                gameStarted = false;
                document.getElementById('btnStartGame').textContent = 'Игра завершена';
                setTimeout(() => {
                  showVictoryModal('Победила команда справа!');
                  // Сбрасываем счет после показа модального окна
                  setTimeout(() => {
                    scoreLeft = 0;
                    scoreRight = 0;
                    updateScoreboard();
                    localStorage.setItem('court_score_left', String(scoreLeft));
                    localStorage.setItem('court_score_right', String(scoreRight));
                    // Возвращаем кнопку в исходное состояние
                    document.getElementById('btnStartGame').textContent = 'Начать игру';
                    document.getElementById('btnStartGame').disabled = false;
                  }, 2000); // Сбрасываем через 2 секунды после показа модального окна
                }, 100);
                return true;
              }
              return false;
            }

            function showVictoryModal(message) {
              document.getElementById('victoryMessage').textContent = message;
              document.getElementById('victoryModal').style.display = 'block';
            }

            function closeVictoryModal() {
              document.getElementById('victoryModal').style.display = 'none';
            }

            function checkGameReady() {
              const allNamesFilled = ids.every(id => {
                const value = document.getElementById(id).value.trim();
                return value !== '';
              });
              
              const startButton = document.getElementById('btnStartGame');
              if (allNamesFilled && !gameStarted) {
                startButton.disabled = false;
              } else {
                startButton.disabled = true;
              }
            }

            function startGame() {
              console.log('Начинаем игру...');
              // Сохраняем состояние перед началом игры
              saveGameState();
              
              gameStarted = true;
              console.log('gameStarted установлен в:', gameStarted);
              currentGameId = generateGameId();
              gameEndTime = null;
              journalEntries = []; // Очищаем журнал для новой игры
              updateJournalDisplay();
              
              document.getElementById('btnStartGame').disabled = true;
              document.getElementById('btnStartGame').textContent = 'Игра началась';
              console.log('Игра началась успешно');
            }

            function getCurrentTime() {
              const now = new Date();
              return now.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
            }

            function getPlayerName(position) {
              return document.getElementById('name_' + position).value || 'Игрок ' + position;
            }

            function getReceivingPlayer(servingPosition) {
              // Определяем принимающего игрока (центрально-симметрично)
              if (servingPosition === 'top_left') return 'top_right';
              if (servingPosition === 'bottom_left') return 'bottom_right';
              if (servingPosition === 'top_right') return 'top_left';
              if (servingPosition === 'bottom_right') return 'bottom_left';
              return 'unknown';
            }

            function addJournalEntry(servingPosition, isSuccess) {
              if (!gameStarted) return;
              
              const servingPlayer = getPlayerName(servingPosition);
              const receivingPosition = getReceivingPlayer(servingPosition);
              const receivingPlayer = getPlayerName(receivingPosition);
              const currentTime = getCurrentTime();
              
              const entry = {
                servingPlayer: servingPlayer,
                receivingPlayer: receivingPlayer,
                isSuccess: isSuccess,
                time: currentTime,
                timestamp: new Date(),
                scoreAfter: `${scoreLeft}:${scoreRight}` // Добавляем счёт после подачи
              };
              
              journalEntries.push(entry);
              updateJournalDisplay();
            }

            function updateJournalDisplay() {
              const journalContent = document.getElementById('journalContent');
              
              if (journalEntries.length === 0) {
                journalContent.innerHTML = '<div class="journal-placeholder">Журнал начнет заполняться после начала игры</div>';
                return;
              }
              
              let html = '';
              journalEntries.forEach(entry => {
                const resultClass = entry.isSuccess ? 'success' : 'returned';
                const resultText = entry.isSuccess ? 'Очко получено' : 'Подача отбита';
                
                html += `
                  <div class="journal-entry ${resultClass}">
                    <div class="entry-time">${entry.time}</div>
                    <div class="entry-players">${entry.servingPlayer} → ${entry.receivingPlayer}</div>
                    <div class="entry-result ${resultClass}">${resultText}</div>
                    <div class="entry-score">Счёт: ${entry.scoreAfter || '0:0'}</div>
                  </div>
                `;
              });
              
              journalContent.innerHTML = html;
              
              // Прокручиваем к последней записи
              journalContent.scrollTop = journalContent.scrollHeight;
            }

            function clearJournal() {
              journalEntries = [];
              updateJournalDisplay();
            }

            function generateGameId() {
              return 'game_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
            }

            function showStatistics() {
              if (journalEntries.length === 0) {
                alert('Нет данных для статистики');
                return;
              }
              
              // Простая статистика
              const totalServes = journalEntries.length;
              const successfulServes = journalEntries.filter(entry => entry.isSuccess).length;
              const successRate = Math.round((successfulServes / totalServes) * 100);
              
              const statsContent = document.getElementById('journalContent');
              statsContent.innerHTML = `
                <div class="stats-content">
                  <h4>Статистика игры</h4>
                  <div class="game-summary">
                    <h5>Общая статистика:</h5>
                    <p>Всего подач: ${totalServes}</p>
                    <p>Успешных подач: ${successfulServes}</p>
                    <p>Процент успеха: ${successRate}%</p>
                  </div>
                </div>
              `;
            }

            function toggleJournalSize() {
              const container = document.querySelector('.journal-container');
              container.classList.toggle('expanded');
              
              const btn = document.getElementById('btnExpandJournal');
              btn.textContent = container.classList.contains('expanded') ? '📕' : '📖';
            }

            function toggleJournalVisibility() {
              const container = document.querySelector('.journal-container');
              const btn = document.getElementById('btnToggleJournal');
              
              container.classList.toggle('visible');
              
              if (container.classList.contains('visible')) {
                btn.textContent = '📋 Скрыть журнал';
                btn.style.backgroundColor = '#f44336';
              } else {
                btn.textContent = '📋 Журнал подач';
                btn.style.backgroundColor = '';
              }
            }

            function updateShuttlecockDisplay() {
              // Если анимация уже идет, не запускаем новую
              if (isAnimating) return;
              
              // Находим текущий видимый волан
              const currentIndicator = document.querySelector('.server-indicator[style*="display: block"]');
              
              if (currentIndicator) {
                // Устанавливаем флаг анимации
                isAnimating = true;
                
                // Получаем координаты текущей и целевой позиций
                const currentRect = currentIndicator.getBoundingClientRect();
                const targetSegment = document.getElementById(shuttlecockPosition);
                const targetIndicator = targetSegment.querySelector('.server-indicator');
                
                // Показываем целевой волан, чтобы получить его координаты
                targetIndicator.style.display = 'block';
                const targetRect = targetIndicator.getBoundingClientRect();
                targetIndicator.style.display = 'none';
                
                // Вычисляем смещение для анимации
                const deltaX = targetRect.left - currentRect.left;
                const deltaY = targetRect.top - currentRect.top;
                
                // Применяем transform для анимации
                currentIndicator.style.transform = `translate(${deltaX}px, ${deltaY}px)`;
                currentIndicator.style.zIndex = '1000';
                
                // После завершения анимации перемещаем волан в целевую позицию
                setTimeout(() => {
                  // Сбрасываем transform
                  currentIndicator.style.transform = '';
                  currentIndicator.style.zIndex = '';
                  
                  // Скрываем текущий волан и показываем в целевой позиции
                  currentIndicator.style.display = 'none';
                  targetIndicator.style.display = 'block';
                  
                  // Сбрасываем флаг анимации
                  isAnimating = false;
                }, 200);
              } else {
                // Если волан не найден, просто показываем в целевой позиции
                document.querySelectorAll('.server-indicator').forEach(el => el.style.display = 'none');
                const targetSegment = document.getElementById(shuttlecockPosition);
                const targetIndicator = targetSegment.querySelector('.server-indicator');
                if (targetIndicator) {
                  targetIndicator.style.display = 'block';
                }
              }
            }

            function moveShuttlecock(side) {
              if (side === 'left') {
                shuttlecockPosition = shuttlecockPosition === 'top_left' ? 'bottom_left' : 'top_left';
              } else {
                shuttlecockPosition = shuttlecockPosition === 'top_right' ? 'bottom_right' : 'top_right';
              }
              updateShuttlecockDisplay();
              localStorage.setItem('court_shuttlecock_position', shuttlecockPosition);
            }

            function swapPlayers(side) {
              if (side === 'left') {
                const topValue = document.getElementById('name_top_left').value;
                const bottomValue = document.getElementById('name_bottom_left').value;
                document.getElementById('name_top_left').value = bottomValue;
                document.getElementById('name_bottom_left').value = topValue;
              } else {
                const topValue = document.getElementById('name_top_right').value;
                const bottomValue = document.getElementById('name_bottom_right').value;
                document.getElementById('name_top_right').value = bottomValue;
                document.getElementById('name_bottom_right').value = topValue;
              }
            }

            function moveShuttlecockBetweenSides() {
              // Сохраняем состояние перед изменением
              saveGameState();
              
              // Перемещаем волан по часовой стрелке: top_right → top_left → bottom_left → bottom_right → top_right
              if (shuttlecockPosition === 'top_right') {
                shuttlecockPosition = 'top_left';
              } else if (shuttlecockPosition === 'top_left') {
                shuttlecockPosition = 'bottom_left';
              } else if (shuttlecockPosition === 'bottom_left') {
                shuttlecockPosition = 'bottom_right';
              } else if (shuttlecockPosition === 'bottom_right') {
                shuttlecockPosition = 'top_right';
              }
              updateShuttlecockDisplay();
              localStorage.setItem('court_shuttlecock_position', shuttlecockPosition);
            }

            function addPointLeft() {
              console.log('addPointLeft вызвана, gameStarted:', gameStarted);
              if (!gameStarted) {
                console.log('Игра не началась, выходим');
                return; // Игра не началась
              }
              
              // Сохраняем состояние перед изменением
              saveGameState();
              
              // Проверяем, находится ли волан на левой стороне
              const isShuttlecockOnLeft = shuttlecockPosition.includes('left');
              
              if (isShuttlecockOnLeft) {
                // Волан на левой стороне - перемещаем и меняем игроков (подающая команда)
                scoreLeft += 1;
                updateScoreboard();
                localStorage.setItem('court_score_left', String(scoreLeft));
                addJournalEntry(shuttlecockPosition, true); // Успешная подача
                moveShuttlecock('left');
                swapPlayers('left');
                checkVictory();
              } else {
                // Волан НЕ на левой стороне - принимающая команда выиграла
                // Добавляем очко сначала, чтобы учесть новый счет
                scoreLeft += 1;
                
                // Проверяем четность нового счета левой команды
                if (scoreLeft % 2 === 0) {
                  // Четное количество очков - подача из верхнего квадрата для левой стороны
                  shuttlecockPosition = 'top_left';
                } else {
                  // Нечетное количество очков - подача из нижнего квадрата для левой стороны
                  shuttlecockPosition = 'bottom_left';
                }
                
                updateShuttlecockDisplay();
                localStorage.setItem('court_shuttlecock_position', shuttlecockPosition);
                updateScoreboard();
                localStorage.setItem('court_score_left', String(scoreLeft));
                addJournalEntry(shuttlecockPosition, false); // Подача отбита
                checkVictory();
                return; // Выходим, чтобы не дублировать обновление счета
              }
            }

            function addPointRight() {
              if (!gameStarted) return; // Игра не началась
              
              // Сохраняем состояние перед изменением
              saveGameState();
              
              // Проверяем, находится ли волан на правой стороне
              const isShuttlecockOnRight = shuttlecockPosition.includes('right');
              
              if (isShuttlecockOnRight) {
                // Волан на правой стороне - перемещаем и меняем игроков (подающая команда)
                scoreRight += 1;
                updateScoreboard();
                localStorage.setItem('court_score_right', String(scoreRight));
                addJournalEntry(shuttlecockPosition, true); // Успешная подача
                moveShuttlecock('right');
                swapPlayers('right');
                checkVictory();
              } else {
                // Волан НЕ на правой стороне - принимающая команда выиграла
                // Добавляем очко сначала, чтобы учесть новый счет
                scoreRight += 1;
                
                // Проверяем четность нового счета правой команды
                if (scoreRight % 2 === 0) {
                  // Четное количество очков - подача из нижнего квадрата для правой стороны
                  shuttlecockPosition = 'bottom_right';
                } else {
                  // Нечетное количество очков - подача из верхнего квадрата для правой стороны
                  shuttlecockPosition = 'top_right';
                }
                
                updateShuttlecockDisplay();
                localStorage.setItem('court_shuttlecock_position', shuttlecockPosition);
                updateScoreboard();
                localStorage.setItem('court_score_right', String(scoreRight));
                addJournalEntry(shuttlecockPosition, false); // Подача отбита
                checkVictory();
                return; // Выходим, чтобы не дублировать обновление счета
              }
            }


            document.getElementById('btnSave').addEventListener('click', save);
            document.getElementById('btnClear').addEventListener('click', clearAll);
            document.getElementById('btnUndo').addEventListener('click', undoLastAction);
            // btnPlusLeft и btnPlusRight удалены, очки добавляются кликом по корту
            document.getElementById('btnMoveShuttlecock').addEventListener('click', moveShuttlecockBetweenSides);
            document.getElementById('btnStartGame').addEventListener('click', startGame);
            document.getElementById('btnToggleJournal').addEventListener('click', toggleJournalVisibility);
            document.getElementById('btnExpandJournal').addEventListener('click', toggleJournalSize);
            document.getElementById('btnShowStats').addEventListener('click', showStatistics);
            
            // Обработчики кликов по корту
            document.getElementById('court_left').addEventListener('click', function(event) {
              // Предотвращаем срабатывание при клике на поля ввода
              if (event.target.tagName !== 'INPUT') {
                // Добавляем визуальную обратную связь
                this.classList.add('clicked');
                setTimeout(() => this.classList.remove('clicked'), 300);
                addPointLeft();
              }
            });
            
            document.getElementById('court_right').addEventListener('click', function(event) {
              // Предотвращаем срабатывание при клике на поля ввода
              if (event.target.tagName !== 'INPUT') {
                // Добавляем визуальную обратную связь
                this.classList.add('clicked');
                setTimeout(() => this.classList.remove('clicked'), 300);
                addPointRight();
              }
            });
            
            // Проверяем готовность к игре при изменении полей ввода
            ids.forEach(id => {
              document.getElementById(id).addEventListener('input', checkGameReady);
            });
            
            // Закрытие модального окна по клику вне его области
            window.addEventListener('click', function(event) {
              const modal = document.getElementById('victoryModal');
              if (event.target === modal) {
                closeVictoryModal();
              }
            });
            
            load();
            
            // Дополнительная проверка готовности после загрузки
            setTimeout(() => {
              checkGameReady();
            }, 100);
          </script>
        </body>
        </html>
        """
    )


def main() -> int:
    program_dir = os.path.dirname(os.path.abspath(__file__))
    out_path = os.path.join(program_dir, "badminton_court.html")
    html = build_html()
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"HTML сохранён: {out_path}")
    try:
        webbrowser.open(f"file://{out_path}")
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())