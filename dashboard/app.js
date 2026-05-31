let currentEmployeeId = "EMP101";

function switchTab(tabName) {
  // Update buttons
  const buttons = document.querySelectorAll('.tab-btn');
  buttons.forEach(btn => {
    if (btn.getAttribute('onclick').includes(tabName)) {
      btn.classList.add('active');
    } else {
      btn.classList.remove('active');
    }
  });

  // Update panels
  const compliancePanel = document.getElementById('compliance-panel');
  const operationsPanel = document.getElementById('operations-panel');

  if (tabName === 'compliance') {
    compliancePanel.classList.add('active');
    operationsPanel.classList.remove('active');
  } else {
    compliancePanel.classList.remove('active');
    operationsPanel.classList.add('active');
  }
}

function renderDashboard(empId) {
  const data = employeeData[empId];
  if (!data) return;

  // Render joining date dynamically
  document.getElementById('join-date-badge').innerText = `Joined: ${data.join_date || '--'}`;

  // Compute points dynamically from the history log on or before today (2026-05-31)
  const todayVal = new Date("2026-05-31");
  let currentPoints = data.starting_points;
  
  // Filter history to include only events on or before today
  const historicalEvents = data.history.filter(item => new Date(item.date) <= todayVal);
  if (historicalEvents.length > 0) {
    currentPoints = historicalEvents[historicalEvents.length - 1].balance;
  }

  // 1. Header Information & Roles
  document.getElementById('role-val').innerText = data.role.split(' ')[0] + ' ' + (data.role.split(' ')[1] || 'Staff');
  document.getElementById('dept-val').innerText = data.department;

  // 2. Compliance Metrics
  document.getElementById('points-val').innerText = currentPoints.toFixed(1);
  document.getElementById('freebies-val').innerText = data.freebies_used;
  
  // Render freebie date links
  const freebieDates = data.history.filter(item => item.code === 'Lo' && item.points === 0 && (item.details.includes('Freebie') || item.details.includes('Lo')));
  const freebieDatesContainer = document.getElementById('freebie-dates');
  freebieDatesContainer.innerHTML = '';
  if (freebieDates.length > 0) {
    freebieDates.forEach((ev, idx) => {
      const a = document.createElement('a');
      a.href = `#row-${ev.date}`;
      a.style.color = '#1d4ed8';
      a.style.textDecoration = 'underline';
      a.style.cursor = 'pointer';
      a.style.fontWeight = '500';
      a.innerText = ev.date;
      a.onclick = (e) => {
        e.preventDefault();
        scrollToRow(`row-${ev.date}`);
      };
      freebieDatesContainer.appendChild(a);
      if (idx < freebieDates.length - 1) {
        const span = document.createElement('span');
        span.innerText = '|';
        span.style.color = 'var(--text-muted)';
        freebieDatesContainer.appendChild(span);
      }
    });
  } else {
    freebieDatesContainer.innerHTML = '<span style="color: var(--text-muted);">None used</span>';
  }
  
  // Status Badge
  const badge = document.getElementById('warning-badge');
  badge.className = 'badge';
  if (currentPoints <= 0.0) {
    badge.innerText = 'TERMINATION TRIGGERED';
    badge.classList.add('badge-danger');
  } else if (currentPoints <= 1.0) {
    badge.innerText = 'TERMINATION WARNING';
    badge.classList.add('badge-danger');
  } else if (currentPoints <= 2.0) {
    badge.innerText = 'WRITTEN WARNING ACTIVE';
    badge.classList.add('badge-warning');
  } else {
    badge.innerText = 'GOOD STANDING';
    badge.classList.add('badge-success');
  }

  // Freeze Status
  const freezeVal = document.getElementById('freeze-val');
  const freezeSub = document.getElementById('freeze-sublabel');
  const activeFreeze = data.freeze_history.find(f => f.status === 'Active');
  if (activeFreeze) {
    freezeVal.innerText = 'ACTIVE';
    freezeVal.style.color = '#ef4444';
    freezeSub.innerText = `Freeze active until ${activeFreeze.end}`;
  } else if (data.freeze_history.length > 0) {
    freezeVal.innerText = 'PAST';
    freezeVal.style.color = '#f59e0b';
    freezeSub.innerText = `Last freeze ended: ${data.freeze_history[data.freeze_history.length - 1].end}`;
  } else {
    freezeVal.innerText = 'NONE';
    freezeVal.style.color = '';
    freezeSub.innerText = 'No active roll-on freezes';
  }

  // Counts
  document.getElementById('fmla-count').innerText = data.fmla_approved_cases;
  document.getElementById('excused-count').innerText = data.excused_absences;

  // 3. Trajectory Table
  const trajectoryBody = document.querySelector('#trajectory-table tbody');
  trajectoryBody.innerHTML = '';
  [...data.history].reverse().forEach(item => {
    const tr = document.createElement('tr');
    tr.id = `row-${item.date}`;
    
    let pointsText = '0.0';
    let ptsClass = '';
    if (item.points < 0) {
      pointsText = `${item.points.toFixed(1)}`;
      ptsClass = 'style="color: #ef4444; font-weight: 600;"';
    } else if (item.points > 0) {
      pointsText = `+${item.points.toFixed(1)}`;
      ptsClass = 'style="color: #10b981; font-weight: 600;"';
    }
    
    let statusHtml = item.status;
    if (item.status === 'Exempted' || item.points === 0) {
      statusHtml = `<span style="cursor: pointer; text-decoration: underline; color: #1d4ed8;" onclick="showExemptionModal('${empId}', '${item.date}')">${item.status} 🔍</span>`;
    }
    
    tr.innerHTML = `
      <td>${item.date}</td>
      <td><code>${item.code}</code></td>
      <td ${ptsClass}>${pointsText}</td>
      <td><strong>${item.balance.toFixed(1)}</strong></td>
      <td>${statusHtml}</td>
      <td>${item.roll_on || '--'}</td>
    `;
    trajectoryBody.appendChild(tr);
  });

  // 4. Exemption & FMLA Explorer
  const exemptionLog = document.getElementById('exemptions-log');
  exemptionLog.innerHTML = '';
  const exemptions = [...data.schedule].reverse().filter(s => s.status.includes('Exempt') || s.status.includes('Excused'));
  if (exemptions.length === 0) {
    exemptionLog.innerHTML = '<p style="color: var(--text-muted);">No exceptions logged.</p>';
  } else {
    exemptions.forEach(ex => {
      const div = document.createElement('div');
      div.style.padding = '0.8rem';
      div.style.background = 'rgba(255,255,255,0.03)';
      div.style.borderRadius = '8px';
      div.style.borderLeft = '3px solid #a855f7';
      div.innerHTML = `
        <div style="display:flex; justify-content:space-between; margin-bottom:0.2rem;">
          <strong style="font-size:0.85rem;">${ex.date} - ${ex.actual}</strong>
          <span style="font-size:0.75rem; color:#10b981;">${ex.status}</span>
        </div>
        <p style="color:var(--text-secondary); font-size:0.8rem; line-height:1.2;">${ex.notes}</p>
        ${ex.supervisor_note ? `<p style="color:var(--text-muted); font-size:0.75rem; margin-top:0.3rem; font-style:italic;">Note: "${ex.supervisor_note}"</p>` : ''}
      `;
      exemptionLog.appendChild(div);
    });
  }

  // 5. Operations: Schedule Table
  const scheduleBody = document.querySelector('#schedule-table tbody');
  scheduleBody.innerHTML = '';
  [...data.schedule].reverse().forEach(item => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${item.date}</td>
      <td>${item.base}</td>
      <td><strong>${item.actual}</strong></td>
      <td>${item.notes || '--'}</td>
    `;
    scheduleBody.appendChild(tr);
  });

  // 6. Operations: Balances
  document.getElementById('sick-bal-val').innerText = `${data.sick_balance_hours} hrs`;
  document.getElementById('vacation-val').innerText = `${data.vacation_hours} hrs`;

  // 7. Operations: Supervisor Notes
  const supervisorLog = document.getElementById('supervisor-notes-log');
  supervisorLog.innerHTML = '';
  const notesWithSupervisor = data.schedule.filter(s => s.supervisor_note);
  if (notesWithSupervisor.length === 0) {
    supervisorLog.innerHTML = '<p style="color: var(--text-muted);">No supervisor notes recorded.</p>';
  } else {
    notesWithSupervisor.forEach(n => {
      const div = document.createElement('div');
      div.style.padding = '0.8rem';
      div.style.background = 'rgba(255,255,255,0.02)';
      div.style.borderRadius = '8px';
      div.innerHTML = `
        <div style="display:flex; justify-content:space-between; font-size:0.8rem; margin-bottom:0.3rem;">
          <span style="color:var(--text-secondary);">${n.date}</span>
          <span style="color:var(--text-muted);">Code: ${n.actual}</span>
        </div>
        <p style="font-size:0.85rem; font-style:italic;">"${n.supervisor_note}"</p>
      `;
      supervisorLog.appendChild(div);
    });
  }

  // 8. Operations: DTO Swaps
  const dtoLog = document.getElementById('dto-log');
  dtoLog.innerHTML = '';
  const trades = data.schedule.filter(s => s.dto);
  if (trades.length === 0) {
    dtoLog.innerHTML = '<p style="color: var(--text-muted);">No shift swaps recorded.</p>';
  } else {
    trades.forEach(t => {
      const div = document.createElement('div');
      div.style.padding = '0.8rem';
      div.style.background = 'rgba(255,255,255,0.02)';
      div.style.borderRadius = '8px';
      div.innerHTML = `
        <div style="font-size:0.85rem;">
          📅 <strong>${t.date}</strong> - Traded with <strong>${t.trade_partner}</strong>
        </div>
        <p style="color:var(--text-secondary); font-size:0.8rem; margin-top:0.2rem;">${t.notes}</p>
      `;
      dtoLog.appendChild(div);
    });
  }

  // Reset letter preview
  document.getElementById('letter-preview').innerText = 'Select an option from the Compliance Action Hub to generate and view the warning memo.';
}

function showLetter(type) {
  const data = employeeData[currentEmployeeId];
  if (!data) return;

  const preview = document.getElementById('letter-preview');
  let level = '';
  
  if (type === 'written') {
    level = 'Written Warning (<= 2.0)';
  } else if (type === 'termination-warning') {
    level = 'Termination Warning (<= 1.0)';
  } else {
    level = 'Termination Memo (<= 0.0)';
  }

  const todayStr = new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });

  preview.innerHTML = `
<strong>OFFICIAL COMPLIANCE NOTICE</strong>
--------------------------------------------------
<strong>Date:</strong> ${todayStr}
<strong>To:</strong> Employee ID: ${currentEmployeeId} (${data.name})
<strong>From:</strong> Workforce Compliance Department
<strong>Subject:</strong> ATTENDANCE COMPLIANCE ACTION NOTICE - ${level.toUpperCase()}

This official document serves as a compliance notice regarding your point balance under the company's No-Fault attendance policy.

<strong>Status Summary:</strong>
- Starting point balance: ${data.starting_points.toFixed(1)} Points
- Current compliance score: ${data.current_points.toFixed(1)} Points
- Current Policy Tier status: <strong>[${level}]</strong>

<strong>Important Notice:</strong>
- Scores below 2.0 trigger a Written Warning.
- Scores below 1.0 trigger a Termination Warning and a 4-month point roll-on freeze.
- Scores at or below 0.0 result in the initiation of termination protocols.

Please review your chronological history and coordinate with HR or your supervisor immediately.

--------------------------------------------------
*Signed, Workforce Compliance Division Office*
  `;
}

// Event Listeners
document.getElementById('employee-select').addEventListener('change', (e) => {
  currentEmployeeId = e.target.value;
  renderDashboard(currentEmployeeId);
});

function scrollToRow(id) {
  const element = document.getElementById(id);
  if (element) {
    element.scrollIntoView({ behavior: 'smooth', block: 'center' });
    // Flash highlight style
    element.style.transition = 'background-color 0.3s ease';
    element.style.backgroundColor = '#dbeafe'; // Light blue highlight
    setTimeout(() => {
      element.style.backgroundColor = '';
    }, 1500);
  }
}

function showExemptionModal(empId, date) {
  const data = employeeData[empId];
  if (!data) return;

  const record = data.history.find(h => h.date === date);
  const scheduleItem = data.schedule.find(s => s.date === date);
  if (!record) return;

  const modal = document.getElementById('exemption-modal');
  const modalContent = document.getElementById('modal-content');

  const supNote = (scheduleItem && scheduleItem.supervisor_note) ? scheduleItem.supervisor_note : "No supervisor notes recorded for this date.";

  modalContent.innerHTML = `
    <div style="margin-bottom: 1rem;">
      <strong>Date:</strong> ${record.date}<br>
      <strong>Infraction Code:</strong> <code>${record.code}</code><br>
      <strong>Points Deducted:</strong> ${record.points.toFixed(1)}<br>
      <strong>Reason/Details:</strong> ${record.details}<br>
    </div>
    <div style="border-top: 1px solid rgba(0,0,0,0.1); padding-top: 1rem; margin-top: 1rem;">
      <strong>Supervisor Notes:</strong>
      <p style="font-style: italic; background: #f8fafc; padding: 0.8rem; border-radius: 8px; margin-top: 0.5rem; border-left: 3px solid #3b82f6; color: var(--text-primary);">
        "${supNote}"
      </p>
    </div>
  `;

  modal.style.display = 'flex';
}

function closeModal() {
  document.getElementById('exemption-modal').style.display = 'none';
}

// Close modal when clicking outside of the modal card
window.onclick = function(event) {
  const modal = document.getElementById('exemption-modal');
  if (event.target === modal) {
    closeModal();
  }
};

// Init
window.onload = () => {
  renderDashboard(currentEmployeeId);
};
