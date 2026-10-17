/* No API credentials or Eventbrite requests run in visitors' browsers. */
document.querySelectorAll('.event-sync-note').forEach(function (note) {
  const verified = Date.parse(note.dataset.lastSync);
  if (Number.isFinite(verified) && Date.now() - verified > 36 * 60 * 60 * 1000) {
    const link = note.querySelector('a');
    note.textContent = 'Event updates are delayed. Showing events last verified on ' + note.dataset.lastSync + '. ';
    if (link) note.appendChild(link);
  }
});
