"use client";

import { useCallback, useEffect, useState } from "react";
import { ArrowLeft, ChevronRight } from "lucide-react";

import { DriversView, PeersView, SectorView } from "@/components/scan/detail";
import { Movers } from "@/components/scan/movers";
import { StockLoading, StockView } from "@/components/scan/stock";
import { Button } from "@/components/ui/button";
import { usePoll } from "@/hooks/use-poll";
import { api, type MoversPayload, type SectorDetail, type StockScan } from "@/lib/api";
import { cn } from "@/lib/utils";

const MOVERS_POLL_MS = 5000;
type Level = "movers" | "stock" | "peers" | "sector" | "drivers";

const DETAIL_LABEL: Record<string, string> = {
  peers: "Peer group",
  sector: "Sector",
  drivers: "Graph drivers",
};

export function Scan({
  perSide,
  onPerSideChange,
}: {
  perSide: number;
  onPerSideChange: (n: number) => void;
}) {
  const [level, setLevel] = useState<Level>("movers");
  const [symbol, setSymbol] = useState<string | null>(null);
  const [scan, setScan] = useState<StockScan | null>(null);
  const [sectorDetail, setSectorDetail] = useState<SectorDetail | null>(null);
  const [searching, setSearching] = useState(false);

  const { data: movers } = usePoll<MoversPayload>(() => api.movers(perSide), MOVERS_POLL_MS, [perSide]);

  const loadStock = useCallback(async (target: string, searchWeb = false) => {
    setScan(null);
    const result = await api.stockScan(target, { searchWeb });
    setScan(result);
    return result;
  }, []);

  const openStock = useCallback(
    (target: string) => {
      setSymbol(target);
      setLevel("stock");
      void loadStock(target);
    },
    [loadStock],
  );

  /** Sector can be opened from the strip, with no stock in focus. */
  const openSector = useCallback(async (name: string) => {
    setSymbol(null);
    setScan(null);
    setLevel("sector");
    setSectorDetail(await api.sectorDetail(name));
  }, []);

  const drill = useCallback(
    async (view: "peers" | "sector" | "drivers") => {
      setLevel(view);
      if (view === "sector" && scan?.sector) setSectorDetail(await api.sectorDetail(scan.sector));
    },
    [scan],
  );

  const searchWeb = useCallback(async () => {
    if (!symbol) return;
    setSearching(true);
    try {
      await loadStock(symbol, true);
    } finally {
      setSearching(false);
    }
  }, [symbol, loadStock]);

  /** Keep the open stock fresh as prices move, without resetting the view. */
  useEffect(() => {
    if (level === "movers" || !symbol) return;
    const timer = setInterval(() => {
      api.stockScan(symbol).then(setScan).catch(() => undefined);
    }, MOVERS_POLL_MS * 3);
    return () => clearInterval(timer);
  }, [level, symbol]);

  const back = () => {
    if (level === "movers") return;
    if (level === "stock" || !symbol) {
      setLevel("movers");
      setSymbol(null);
    } else {
      setLevel("stock");
    }
  };

  return (
    <div className="space-y-4">
      <nav className="bg-muted/40 flex items-center gap-2 rounded-lg border px-3 py-2 text-sm">
        <Crumb active={level === "movers"} onClick={() => { setLevel("movers"); setSymbol(null); }}>
          Movers
        </Crumb>
        {symbol && (
          <>
            <ChevronRight className="text-muted-foreground size-3" />
            <Crumb active={level === "stock"} onClick={() => setLevel("stock")}>
              {symbol}
            </Crumb>
          </>
        )}
        {level !== "movers" && level !== "stock" && (
          <>
            <ChevronRight className="text-muted-foreground size-3" />
            <span className="font-medium">
              {level === "sector" && !symbol ? sectorDetail?.sector.name : DETAIL_LABEL[level]}
            </span>
          </>
        )}
        {level !== "movers" && (
          <Button variant="ghost" size="sm" className="ml-auto h-7" onClick={back}>
            <ArrowLeft className="size-3.5" />
            Back
          </Button>
        )}
      </nav>

      {level === "movers" && (
        <Movers
          data={movers}
          perSide={perSide}
          onPerSideChange={onPerSideChange}
          onPick={openStock}
          onPickSector={openSector}
        />
      )}
      {level === "stock" &&
        (scan ? (
          <StockView scan={scan} searching={searching} onSearchWeb={searchWeb} onDrill={drill} />
        ) : (
          <StockLoading />
        ))}
      {level === "peers" && (scan ? <PeersView scan={scan} /> : <StockLoading />)}
      {level === "drivers" && (scan ? <DriversView scan={scan} /> : <StockLoading />)}
      {level === "sector" && (
        <SectorView detail={sectorDetail} focus={symbol ?? ""} onPick={openStock} />
      )}
    </div>
  );
}

function Crumb({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  if (active) return <span className="font-medium">{children}</span>;
  return (
    <button onClick={onClick} className={cn("text-primary hover:underline")}>
      {children}
    </button>
  );
}
