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
import LoadingScreen from "../components/LoadingScreen.jsx";
import StatusBadge from "../components/StatusBadge.jsx";
import {
  formatClassTitle,
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
      <dt className="text-xs font-semibold uppercase tracking-wide text-[#667085]">
        {label}
      </dt>
      <dd className="mt-1 text-sm font-medium text-[#172033]">{value}</dd>
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
            className="rounded-md bg-[#256f68] px-3 py-2 text-sm font-semibold text-white transition hover:bg-[#1f5d58] focus:outline-none focus:ring-2 focus:ring-[#256f68] focus:ring-offset-2 disabled:cursor-not-allowed disabled:bg-[#8ebbb5]"
          >
            {actionKey === `approve:${membership.id}` ? "Approving..." : "Approve"}
          </button>
          <button
            type="button"
            disabled={isBusy}
            onClick={() => onReject(membership.id)}
            className="rounded-md border border-[#f5b5b5] px-3 py-2 text-sm font-semibold text-[#7f1d1d] transition hover:bg-[#fff1f1] focus:outline-none focus:ring-2 focus:ring-[#b42318] focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {actionKey === `reject:${membership.id}` ? "Rejecting..." : "Reject"}
          </button>
        </div>
      ) : null}

      {canRemove ? (
        <div className="lg:justify-self-end">
          {confirmRemovalId === membership.id ? (
            <div className="flex flex-wrap items-center gap-2 rounded-md border border-[#f5b5b5] bg-[#fff8f8] p-2">
              <span className="text-sm font-medium text-[#7f1d1d]">Remove?</span>
              <button
                type="button"
                disabled={isBusy}
                onClick={() => onConfirmRemove(membership.id)}
                className="rounded-md bg-[#b42318] px-3 py-1.5 text-sm font-semibold text-white transition hover:bg-[#971c14] focus:outline-none focus:ring-2 focus:ring-[#b42318] focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {actionKey === `remove:${membership.id}` ? "Removing..." : "Yes"}
              </button>
              <button
                type="button"
                disabled={isBusy}
                onClick={onCancelRemove}
                className="rounded-md border border-[#cbd5e1] px-3 py-1.5 text-sm font-semibold text-[#344056] transition hover:bg-white focus:outline-none focus:ring-2 focus:ring-[#256f68] focus:ring-offset-2"
              >
                Cancel
              </button>
            </div>
          ) : (
            <button
              type="button"
              onClick={() => onRemovePrompt(membership.id)}
              className="rounded-md border border-[#f5b5b5] px-3 py-2 text-sm font-semibold text-[#7f1d1d] transition hover:bg-[#fff1f1] focus:outline-none focus:ring-2 focus:ring-[#b42318] focus:ring-offset-2"
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
            "This class is not in your memberships. Request access before opening class details.",
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
    return <LoadingScreen message="Loading class details..." />;
  }

  if (error && !classroom) {
    return (
      <section className="space-y-5">
        <Alert title="Could not load class" message={error.message} items={error.items} />
        <Link
          to="/classes/join"
          className="inline-flex rounded-md bg-[#256f68] px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-[#1f5d58] focus:outline-none focus:ring-2 focus:ring-[#256f68] focus:ring-offset-2"
        >
          Request membership
        </Link>
      </section>
    );
  }

  return (
    <section className="space-y-6">
      <div className="rounded-md border border-[#dde4ef] bg-white p-5 shadow-sm sm:p-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <p className="text-sm font-semibold uppercase tracking-wide text-[#256f68]">
              Class details
            </p>
            <h1 className="mt-2 text-3xl font-bold text-[#172033]">
              {classroom.name}
            </h1>
            <p className="mt-3 max-w-2xl text-base leading-7 text-[#566176]">
              {classroom.description || formatClassTitle(classroom)}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <StatusBadge value={membership?.role} />
            <StatusBadge value={membership?.status} />
          </div>
        </div>

        <dl className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <SummaryItem label="Class ID" value={classroom.id} />
          <SummaryItem label="Semester" value={classroom.semester} />
          <SummaryItem label="Section" value={classroom.section} />
          <SummaryItem
            label="Requested"
            value={formatDate(membership?.requested_at)}
          />
          {canManageMembers ? (
            <SummaryItem label="Join code" value={classroom.join_code} />
          ) : null}
        </dl>

        {isApproved(membership) ? (
          <div className="mt-6 flex flex-wrap gap-2 border-t border-[#e5eaf2] pt-5">
            <Link
              to={`/classes/${numericClassId}/courses`}
              className="rounded-md bg-[#256f68] px-4 py-2 text-sm font-semibold text-white transition hover:bg-[#1f5d58] focus:outline-none focus:ring-2 focus:ring-[#256f68] focus:ring-offset-2"
            >
              Class courses
            </Link>
            <Link
              to={`/classes/${numericClassId}/my-courses`}
              className="rounded-md border border-[#cbd5e1] px-4 py-2 text-sm font-semibold text-[#344056] transition hover:bg-white focus:outline-none focus:ring-2 focus:ring-[#256f68] focus:ring-offset-2"
            >
              My courses
            </Link>
          </div>
        ) : null}
      </div>

      {error ? (
        <Alert title="Class action blocked" message={error.message} items={error.items} />
      ) : null}

      {!isApproved(membership) ? (
        <div className="rounded-md border border-[#f2cf82] bg-[#fffaf0] p-5">
          <h2 className="text-lg font-semibold text-[#172033]">
            Membership {membership?.status}
          </h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-[#7a4b00]">
            Protected class content is available only after your membership is
            approved by a class representative.
          </p>
          <Link
            to="/classes"
            className="mt-4 inline-flex rounded-md border border-[#e3bc67] px-4 py-2 text-sm font-semibold text-[#7a4b00] transition hover:bg-white focus:outline-none focus:ring-2 focus:ring-[#ad7815] focus:ring-offset-2"
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
            <div className="rounded-md border border-[#dde4ef] bg-white p-5 shadow-sm sm:p-6">
              <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <h2 className="text-lg font-semibold text-[#172033]">
                    Membership Requests
                  </h2>
                  <p className="mt-1 text-sm text-[#566176]">
                    Pending requests for this class.
                  </p>
                </div>
                <span className="text-sm font-medium text-[#566176]">
                  {requests.length} pending
                </span>
              </div>

              {requests.length === 0 ? (
                <p className="mt-5 rounded-md border border-dashed border-[#cbd5e1] p-4 text-sm text-[#566176]">
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

          <div className="rounded-md border border-[#dde4ef] bg-white p-5 shadow-sm sm:p-6">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h2 className="text-lg font-semibold text-[#172033]">
                  Approved Members
                </h2>
                <p className="mt-1 text-sm text-[#566176]">
                  Current approved membership list.
                </p>
              </div>
              <span className="text-sm font-medium text-[#566176]">
                {members.length} approved
              </span>
            </div>

            {members.length === 0 ? (
              <p className="mt-5 rounded-md border border-dashed border-[#cbd5e1] p-4 text-sm text-[#566176]">
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
