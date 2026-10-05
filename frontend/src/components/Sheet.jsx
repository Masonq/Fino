import { Drawer } from 'vaul'

/**
 * PLONK 2.0: нижняя шторка на Vaul — тянется пальцем вниз, чтобы закрыть (как в iOS), закрывается по фону и
 * Esc, держит фокус внутри. Заголовок обязателен для читалок экрана — без видимого подписываем скрыто.
 */
export default function Sheet({ open, onClose, title, hiddenTitle, className = '', children }) {
  return (
    <Drawer.Root open={open} onOpenChange={(o) => { if (!o) onClose() }} repositionInputs>
      <Drawer.Portal>
        <Drawer.Overlay className="vs-overlay" />
        <Drawer.Content className={`vs-sheet ${className}`} aria-describedby={undefined}>
          <div className="vs-grab" aria-hidden="true" />
          {title ? <Drawer.Title className="jr-title">{title}</Drawer.Title> : <Drawer.Title className="vs-sr">{hiddenTitle}</Drawer.Title>}
          <div className="vs-body">{children}</div>
        </Drawer.Content>
      </Drawer.Portal>
    </Drawer.Root>
  )
}
