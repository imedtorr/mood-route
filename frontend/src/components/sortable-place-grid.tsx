import {
  DndContext,
  KeyboardSensor,
  PointerSensor,
  closestCenter,
  useSensor,
  useSensors,
  type DragEndEvent,
} from "@dnd-kit/core";
import {
  SortableContext,
  arrayMove,
  rectSortingStrategy,
  sortableKeyboardCoordinates,
  useSortable,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { GripVertical } from "lucide-react";
import { PlaceCard } from "@/components/place-card";
import type { Place } from "@/lib/types";
import { cn } from "@/lib/utils";

function SortablePlaceItem({ place, onClick }: { place: Place; onClick: () => void }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: place.id,
  });

  return (
    <div
      ref={setNodeRef}
      id={`place-${place.id}`}
      style={{
        transform: CSS.Transform.toString(transform),
        transition,
      }}
      className={cn("relative", isDragging && "z-10 opacity-60")}
    >
      <button
        type="button"
        className="absolute left-2 top-2 z-10 flex size-8 cursor-grab items-center justify-center rounded-full bg-background/90 text-muted-foreground opacity-80 shadow-sm ring-1 ring-border/60 transition-opacity hover:bg-accent hover:text-accent-foreground hover:opacity-100 active:cursor-grabbing"
        aria-label={`Reorder ${place.title}`}
        onClick={(e) => e.stopPropagation()}
        {...attributes}
        {...listeners}
      >
        <GripVertical className="size-4" />
      </button>
      <PlaceCard place={place} onClick={onClick} />
    </div>
  );
}

export function SortablePlaceGrid({
  places,
  onReorder,
  onPlaceClick,
}: {
  places: Place[];
  onReorder: (nextOrder: string[]) => void;
  onPlaceClick: (place: Place) => void;
}) {
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );

  function handleDragEnd({ active, over }: DragEndEvent) {
    if (!over || active.id === over.id) return;

    const ids = places.map((p) => p.id);
    const oldIndex = ids.indexOf(String(active.id));
    const newIndex = ids.indexOf(String(over.id));
    if (oldIndex === -1 || newIndex === -1) return;

    onReorder(arrayMove(ids, oldIndex, newIndex));
  }

  return (
    <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
      <SortableContext items={places.map((p) => p.id)} strategy={rectSortingStrategy}>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {places.map((place) => (
            <SortablePlaceItem key={place.id} place={place} onClick={() => onPlaceClick(place)} />
          ))}
        </div>
      </SortableContext>
    </DndContext>
  );
}
