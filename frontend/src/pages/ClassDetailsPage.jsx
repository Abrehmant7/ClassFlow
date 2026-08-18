import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";

import {
  getClassroom,
  listClassMembers,
  listJoinRequests,
  listMyClassrooms,
} from "../api/classrooms.js";
import {
  approveMembership,
  rejectMembership,
  removeMembership,
} from "../api/memberships.js";
import { useAuth } from "../auth/useAuth.js";
import Alert from "../components/Alert.jsx";
import ClassWorkspaceHeader from "../components/ClassWorkspaceHeader.jsx";
import LoadingScreen from "../components/LoadingScreen.jsx";
import StatusBadge from "../components/StatusBadge.jsx";
import {
  isApproved,
  isRepresentative,
} from "../utils/classrooms.js";
import { parseApiError } from "../utils/errors.js";

function formatDate(value) {
  if (!value) return "Not set";
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function SummaryItem({ label, value }) {
  return (
    <div>
      <dt className="text-xs font-semibold uppercase tracking-wide text-[#64748B]">
        {label}
      </dt>
      <dd className="mt-1 text-sm font-medium text-[#020617]">{value}</dd>
    </div>
  );
}

function getMemberName(membership) {
  const memberUser = membership.user;

  if (!memberUser) {
    return `User #${membership.user_id}`;
  }

  const fullName = [memberUser.first_name, memberUser.last_name]
    .filter(Boolean)
    .join(" ");

  return fullName || memberUser.username || `User #${membership.user_id}`;
}

function MembershipRow({
  actionKey,
  canRemove,
  confirmRemovalId,
  membership,
  onApprove,
  onCancelRemove,
  onConfirmRemove,
  onReject,
  onRemovePrompt,
  showRequestActions = false,
}) {
  const isBusy = actionKey?.endsWith(`:${membership.id}`);

  return (
    <div className="grid gap-3 border-b border-[#e5eaf2] py-4 last:border-b-0 lg:grid-cols-[1fr_auto] lg:items-center">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        <SummaryItem label="Name" value={getMemberName(membership)} />
        <SummaryItem
          label="Roll number"
          value={membership.user?.roll_number || "Not set"}
        />
        <SummaryItem label="Role" value={<StatusBadge value={membership.role} />} />
        <SummaryItem
          label="Status"
          value={<StatusBadge value={membership.status} />}
        />
        <SummaryItem label="Requested" value={formatDate(membership.requested_at)} />
      </div>

      {showRequestActions ? (
        <div className="flex flex-wrap gap-2 lg:justify-end">
          <button
            type="button"
            disabled={isBusy}
            onClick={() => onApprove(membership.id)}
            className="rounded-md bg-[#2563EB] px-3 py-2 text-sm font-semibold text-white transition hover:bg-[#1D4ED8] focus:outline-none focus:ring-2 focus:ring-[#2563EB] focus:ring-offset-2 disabled:cursor-not-allowed disabled:bg-[#93C5FD]"
          >
            {actionKey === `approve:${membership.id}` ? "Approving..." : "Approve"}
          </button>
          <button
            type="button"
            disabled={isBusy}
            onClick={() => onReject(membership.id)}
            className="rounded-md border border-[#FECACA] px-3 py-2 text-sm font-semibold text-[#B91C1C] transition hover:bg-[#FEF2F2] focus:outline-none focus:ring-2 focus:ring-[#DC2626] focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {actionKey === `reject:${membership.id}` ? "Rejecting..." : "Reject"}
          </button>
        </div>
      ) : null}

      {canRemove ? (
        <div className="lg:justify-self-end">
          {confirmRemovalId === membership.id ? (
            <div className="flex flex-wrap items-center gap-2 rounded-md border border-[#FECACA] bg-[#FEF2F2] p-2">
              <span className="text-sm font-medium text-[#B91C1C]">Remove?</span>
              <button
                type="button"
                disabled={isBusy}
                onClick={() => onConfirmRemove(membership.id)}
                className="rounded-md bg-[#DC2626] px-3 py-1.5 text-sm font-semibold text-white transition hover:bg-[#B91C1C] focus:outline-none focus:ring-2 focus:ring-[#DC2626] focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {actionKey === `remove:${membership.id}` ? "Removing..." : "Yes"}
              </button>
              <button
                type="button"
                disabled={isBusy}
                onClick={onCancelRemove}
                className="rounded-md border border-[#E2E8F0] px-3 py-1.5 text-sm font-semibold text-[#475569] transition hover:bg-white focus:outline-none focus:ring-2 focus:ring-[#2563EB] focus:ring-offset-2"
              >
                Cancel
              </button>
            </div>
          ) : (
            <button
              type="button"
              onClick={() => onRemovePrompt(membership.id)}
              className="rounded-md border border-[#FECACA] px-3 py-2 text-sm font-semibold text-[#B91C1C] transition hover:bg-[#FEF2F2] focus:outline-none focus:ring-2 focus:ring-[#DC2626] focus:ring-offset-2"
            >
              Remove
            </button>
          )}
        </div>
      ) : null}
    </div>
  );
}

function ClassDetailsPage() {
  const { classId } = useParams();
  const { user } = useAuth();
  const numericClassId = Number(classId);
  const [classroom, setClassroom] = useState(null);
  const [membership, setMembership] = useState(null);
  const [members, setMembers] = useState([]);
  const [requests, setRequests] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [actionError, setActionError] = useState(null);
  const [actionMessage, setActionMessage] = useState("");
  const [actionKey, setActionKey] = useState("");
  const [confirmRemovalId, setConfirmRemovalId] = useState(null);

  const canManageMembers = useMemo(
    () => isRepresentative(membership),
    [membership],
  );

  const loadClassData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    setActionError(null);

    try {
      const myClassrooms = await listMyClassrooms();
      const mineRecord = myClassrooms.find(
        (item) => item.id === numericClassId,
      );

      if (!mineRecord) {
        setClassroom(null);
        setMembership(null);
        setMembers([]);
        setRequests([]);
        setError({
          message:
            "This class is not in your memberships. Request access before opening members.",
          items: [],
        });
        return;
      }

      setClassroom(mineRecord);
      setMembership(mineRecord.membership);

      if (!isApproved(mineRecord.membership)) {
        setMembers([]);
        setRequests([]);
        return;
      }

      const [classroomData, memberData, requestData] = await Promise.all([
        getClassroom(numericClassId),
        listClassMembers(numericClassId),
        isRepresentative(mineRecord.membership)
          ? listJoinRequests(numericClassId)
          : Promise.resolve([]),
      ]);

      setClassroom({ ...classroomData, membership: mineRecord.membership });
      setMembers(memberData);
      setRequests(requestData);
    } catch (apiError) {
      setError(parseApiError(apiError));
    } finally {
      setIsLoading(false);
    }
  }, [numericClassId]);

  useEffect(() => {
    loadClassData();
  }, [loadClassData]);

  async function runMembershipAction(action, membershipId, successMessage) {
    setActionKey(`${action}:${membershipId}`);
    setActionError(null);
    setActionMessage("");

    try {
      if (action === "approve") {
        await approveMembership(membershipId);
      } else if (action === "reject") {
        await rejectMembership(membershipId);
      } else {
        await removeMembership(membershipId);
        setConfirmRemovalId(null);
      }

      setActionMessage(successMessage);
      await loadClassData();
    } catch (apiError) {
      setActionError(parseApiError(apiError));
    } finally {
      setActionKey("");
    }
  }

  if (isLoading) {
    return <LoadingScreen message="Loading members..." />;
  }

  if (error && !classroom) {
    return (
      <section className="space-y-5">
        <Alert title="Could not load class" message={error.message} items={error.items} />
        <Link
          to="/classes/join"
          className="inline-flex rounded-md bg-[#2563EB] px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-[#1D4ED8] focus:outline-none focus:ring-2 focus:ring-[#2563EB] focus:ring-offset-2"
        >
          Request membership
        </Link>
      </section>
    );
  }

  return (
    <section className="space-y-6">
      <ClassWorkspaceHeader classroom={classroom} membership={membership} />

      {error ? (
        <Alert title="Class action blocked" message={error.message} items={error.items} />
      ) : null}

      {!isApproved(membership) ? (
        <div className="rounded-md border border-[#FDE68A] bg-[#FFFBEB] p-5">
          <h2 className="text-lg font-semibold text-[#020617]">
            Membership {membership?.status}
          </h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-[#B45309]">
            Protected class content is available only after your membership is
            approved by a class representative.
          </p>
          <Link
            to="/classes"
            className="mt-4 inline-flex rounded-md border border-[#FDE68A] px-4 py-2 text-sm font-semibold text-[#B45309] transition hover:bg-white focus:outline-none focus:ring-2 focus:ring-[#D97706] focus:ring-offset-2"
          >
            Back to My Classes
          </Link>
        </div>
      ) : (
        <>
          {actionError ? (
            <Alert
              title="Action failed"
              message={actionError.message}
              items={actionError.items}
            />
          ) : null}
          {actionMessage ? (
            <Alert type="success" title="Updated" message={actionMessage} />
          ) : null}

          {canManageMembers ? (
            <div className="rounded-md border border-[#E2E8F0] bg-white p-5 shadow-sm sm:p-6">
              <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <h2 className="text-lg font-semibold text-[#020617]">
                    Membership Requests
                  </h2>
                  <p className="mt-1 text-sm text-[#64748B]">
                    Pending requests for this class.
                  </p>
                </div>
                <span className="text-sm font-medium text-[#64748B]">
                  {requests.length} pending
                </span>
              </div>

              {requests.length === 0 ? (
                <p className="mt-5 rounded-md border border-dashed border-[#E2E8F0] p-4 text-sm text-[#64748B]">
                  No pending membership requests.
                </p>
              ) : (
                <div className="mt-4">
                  {requests.map((request) => (
                    <MembershipRow
                      actionKey={actionKey}
                      key={request.id}
                      membership={request}
                      onApprove={(membershipId) =>
                        runMembershipAction(
                          "approve",
                          membershipId,
                          "Membership request approved.",
                        )
                      }
                      onReject={(membershipId) =>
                        runMembershipAction(
                          "reject",
                          membershipId,
                          "Membership request rejected.",
                        )
                      }
                      showRequestActions
                    />
                  ))}
                </div>
              )}
            </div>
          ) : null}

          <div className="rounded-md border border-[#E2E8F0] bg-white p-5 shadow-sm sm:p-6">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h2 className="text-lg font-semibold text-[#020617]">
                  Approved Members
                </h2>
                <p className="mt-1 text-sm text-[#64748B]">
                  Current approved membership list.
                </p>
              </div>
              <span className="text-sm font-medium text-[#64748B]">
                {members.length} approved
              </span>
            </div>

            {members.length === 0 ? (
              <p className="mt-5 rounded-md border border-dashed border-[#E2E8F0] p-4 text-sm text-[#64748B]">
                No approved members were returned by the backend.
              </p>
            ) : (
              <div className="mt-4">
                {members.map((member) => (
                  <MembershipRow
                    actionKey={actionKey}
                    canRemove={
                      canManageMembers &&
                      member.user_id !== user?.id &&
                      member.user_id !== classroom.creator_id
                    }
                    confirmRemovalId={confirmRemovalId}
                    key={member.id}
                    membership={member}
                    onCancelRemove={() => setConfirmRemovalId(null)}
                    onConfirmRemove={(membershipId) =>
                      runMembershipAction(
                        "remove",
                        membershipId,
                        "Member removed from the class.",
                      )
                    }
                    onRemovePrompt={(membershipId) =>
                      setConfirmRemovalId(membershipId)
                    }
                  />
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </section>
  );
}

export default ClassDetailsPage;
