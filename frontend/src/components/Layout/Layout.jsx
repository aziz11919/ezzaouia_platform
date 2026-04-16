import Sidebar from './Sidebar'
import Header from './Header'

export default function Layout({ title, breadcrumb, rightNode, children }) {
  return (
    <div className="app-shell">
      <Sidebar />
      <div className="main-shell">
        <Header title={title} breadcrumb={breadcrumb} rightNode={rightNode} />
        <main className="content">{children}</main>
      </div>
    </div>
  )
}
