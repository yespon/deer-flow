// Marketing layout - for landing and auth pages
import { Inter } from "next/font/google";
import "../../styles/globals.css";

const inter = Inter({ subsets: ["latin"] });

export default function MarketingLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <div className={`${inter.className} antialiased`}>{children}</div>;
}
