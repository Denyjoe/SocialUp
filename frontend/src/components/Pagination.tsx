import { ChevronLeft, ChevronRight } from "lucide-react";
import { useTranslation } from "react-i18next";

interface PaginationProps {
  page: number;
  count: number;
  pageSize?: number;
  onPageChange: (page: number) => void;
}

export function Pagination({ page, count, pageSize = 20, onPageChange }: PaginationProps) {
  const { t } = useTranslation();
  const totalPages = Math.max(1, Math.ceil(count / pageSize));
  if (totalPages <= 1) return null;

  return (
    <div className="pagination">
      <button
        className="btn-secondary btn-sm"
        disabled={page <= 1}
        onClick={() => onPageChange(page - 1)}
      >
        <ChevronLeft size={15} /> {t("common.previous")}
      </button>
      <span>
        {t("common.page")} {page} {t("common.of")} {totalPages} ({count.toLocaleString()} {t("common.total")})
      </span>
      <button
        className="btn-secondary btn-sm"
        disabled={page >= totalPages}
        onClick={() => onPageChange(page + 1)}
      >
        {t("common.next")} <ChevronRight size={15} />
      </button>
    </div>
  );
}
