export async function copyPluginToken(input: HTMLInputElement): Promise<boolean> {
  const select = () => {
    input.focus()
    input.select()
    input.setSelectionRange(0, input.value.length)
  }
  if (navigator.clipboard?.writeText) {
    try { await navigator.clipboard.writeText(input.value); return true } catch { /* HTTP or denied permission */ }
  }
  select()
  try { return document.execCommand('copy') } catch { return false }
}
